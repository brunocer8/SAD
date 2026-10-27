"""API do SAD Solar PME Bahia (login, simulação, dashboard e relatórios). Rodar: uvicorn app:app --reload"""
import hashlib, json, math, os, secrets, sqlite3
from datetime import datetime

import requests
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from financeiro import AreaInsuficiente, carregar_municipios
from saw import decisao

app = FastAPI(title="SAD Solar PME Bahia")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DB = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "sad.db"))


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


with db() as c:
    c.executescript("""
    create table if not exists usuarios(id integer primary key, nome text unique, sal text, hash text);
    create table if not exists sessoes(token text primary key, usuario_id integer);
    create table if not exists simulacoes(id integer primary key, usuario_id integer, criado text, municipio text,
      kwp real, investimento real, payback real, vpl real, classe text, entrada text, resultado text, risco text, texto text);""")


def _hash(senha, sal):
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal), 200_000).hex()


def _sessao(c, uid):
    tok = secrets.token_hex(24)
    c.execute("insert into sessoes values(?,?)", (tok, uid))
    return tok


def usuario(authorization: str = Header(default="")):
    with db() as c:
        r = c.execute("select u.id, u.nome from sessoes s join usuarios u on u.id=s.usuario_id where s.token=?",
                      (authorization.removeprefix("Bearer "),)).fetchone()
    if not r:
        raise HTTPException(401, "Sessão inválida")
    return dict(r)


class Cred(BaseModel):
    nome: str = Field(min_length=3, max_length=40)
    senha: str = Field(min_length=6, max_length=100)


@app.post("/api/registrar")
def registrar(d: Cred):
    sal = secrets.token_hex(16)
    with db() as c:
        try:
            uid = c.execute("insert into usuarios(nome,sal,hash) values(?,?,?)", (d.nome, sal, _hash(d.senha, sal))).lastrowid
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Usuário já existe")
        return {"token": _sessao(c, uid), "nome": d.nome}


@app.post("/api/login")
def login(d: Cred):
    with db() as c:
        u = c.execute("select * from usuarios where nome=?", (d.nome,)).fetchone()
        if not u or not secrets.compare_digest(u["hash"], _hash(d.senha, u["sal"])):
            raise HTTPException(401, "Usuário ou senha incorretos")
        return {"token": _sessao(c, u["id"]), "nome": u["nome"]}


class Entrada(BaseModel):
    cod_ibge: int
    consumo_mes_kwh: float = Field(gt=0)
    tarifa_kwh: float = Field(gt=0)
    area_m2: float | None = None
    financiado: int = 0
    consumo_diurno_fracao: float = Field(0.60, ge=0.1, le=1.0)


def limpar(x):
    if isinstance(x, dict):
        return {k: limpar(v) for k, v in x.items()}
    if isinstance(x, list):
        return [limpar(v) for v in x]
    return None if isinstance(x, float) and not math.isfinite(x) else x


@app.get("/api/municipios")
def municipios():
    mun, _ = carregar_municipios()
    return [{"cod": int(c), "nome": n} for c, n in mun["municipio"].items()]


@app.post("/api/analisar")
def analisar_cliente(e: Entrada, u=Depends(usuario)):
    mun, _ = carregar_municipios()
    if e.cod_ibge not in mun.index:
        raise HTTPException(404, "Município fora da Bahia ou desconhecido")
    ent = e.model_dump()
    try:
        dec = decisao(ent)
    except AreaInsuficiente as ex:
        raise HTTPException(422, str(ex))
    rec = dec["recomendacao"]
    exib = dec["ranking"][rec["indice_exibido"]]   # cenário detalhado nos gráficos (a recomendada, ou a de maior VPL se não instalar)
    risco = exib["risco"]
    classe = "Não instalar" if rec["tipo"] == "nao_instalar" else max(risco["prob_classe"], key=risco["prob_classe"].get)
    base = {**exib["res"], "decisao": dec, "veredito": exib["veredito"]}
    out = limpar({"entrada": ent, "resultado": base, "risco": risco})
    with db() as c:
        sid = c.execute("insert into simulacoes(usuario_id,criado,municipio,kwp,investimento,payback,vpl,classe,entrada,resultado,risco)"
                        " values(?,?,?,?,?,?,?,?,?,?,?)",
                        (u["id"], datetime.now().strftime("%Y-%m-%d %H:%M"), base["municipio"], base["kwp"], base["investimento"],
                         out["resultado"]["payback"], base["vpl"], classe, json.dumps(out["entrada"]),
                         json.dumps(out["resultado"]), json.dumps(out["risco"]))).lastrowid
    return {"id": sid, **out}


@app.post("/api/texto")
def texto(d: dict, u=Depends(usuario)):
    r, k = d["resultado"], d["risco"]
    pb = f"{r['payback']:.1f} anos" if r.get("payback") is not None else "não se paga na vida útil"
    resumo = (f"Município: {r['municipio']}. kWp do cenário analisado: {r['kwp']:.0f}. Investimento: R$ {r['investimento']:,.0f}. "
              f"Payback à vista: {pb}. VPL: R$ {r['vpl']:,.0f}. Cobertura do consumo: {r['cobertura_consumo']:.0%}. "
              f"Em {k['n_cenarios']} cenários com incerteza: VPL positivo em {k['prob_vpl_positivo']:.0%}; faixas de retorno {k['prob_classe']}; "
              f"financiado melhor que à vista em {k['prob_financiado_melhor']:.0%}." + (" Contexto da decisão multicritério (SAW): " + d["contexto"] if d.get("contexto") else ""))
    prompt = ("Você apoia a decisão de uma pequena empresa sobre instalar energia solar. Escreva 3 parágrafos curtos, em português, para um "
              "gestor leigo: (1) o que o resultado indica, (2) riscos e incertezas, (3) recomendação prática. Use SOMENTE os números "
              "abaixo, não invente valores. Lembre que são simulações baseadas em premissas.\n\n" + resumo)
    txt, fonte = resumo + " (Texto automático: defina GEMINI_API_KEY para a análise por IA.)", "padrao"
    if os.getenv("GEMINI_API_KEY"):
        try:
            resp = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
                                 params={"key": os.environ["GEMINI_API_KEY"]}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
            resp.raise_for_status()
            txt, fonte = resp.json()["candidates"][0]["content"]["parts"][0]["text"], "gemini"
        except Exception as ex:
            print("Gemini falhou:", ex)
    if d.get("id"):
        with db() as c:
            c.execute("update simulacoes set texto=? where id=? and usuario_id=?", (txt, d["id"], u["id"]))
    return {"texto": txt, "fonte": fonte}


@app.get("/api/simulacoes")
def listar(u=Depends(usuario)):
    with db() as c:
        rows = c.execute("select id,criado,municipio,kwp,investimento,payback,vpl,classe from simulacoes where usuario_id=? order by id desc",
                         (u["id"],)).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/simulacoes/{sid}")
def detalhe(sid: int, u=Depends(usuario)):
    with db() as c:
        r = c.execute("select * from simulacoes where id=? and usuario_id=?", (sid, u["id"])).fetchone()
    if not r:
        raise HTTPException(404, "Simulação não encontrada")
    d = dict(r)
    for k in ("entrada", "resultado", "risco"):
        d[k] = json.loads(d[k])
    return d


@app.delete("/api/simulacoes/{sid}")
def excluir(sid: int, u=Depends(usuario)):
    with db() as c:
        c.execute("delete from simulacoes where id=? and usuario_id=?", (sid, u["id"]))
    return {"ok": True}


@app.get("/api/dashboard")
def dashboard(u=Depends(usuario)):
    rows = listar(u)
    n = len(rows)
    pbs = [r["payback"] for r in rows if r["payback"] is not None]
    cont = lambda k: {v: sum(1 for r in rows if r[k] == v) for v in {r[k] for r in rows}}
    return {"total": n, "payback_medio": sum(pbs) / len(pbs) if pbs else None, "vpl_total": sum(r["vpl"] for r in rows),
            "kwp_total": sum(r["kwp"] for r in rows), "investimento_total": sum(r["investimento"] for r in rows),
            "por_classe": cont("classe"), "por_municipio": cont("municipio"), "recentes": rows[:5]}


app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")
