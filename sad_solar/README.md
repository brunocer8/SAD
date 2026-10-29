# Sol da Bahia: SAD de viabilidade de energia solar para PMEs baianas

Sistema de Apoio à Decisão (disciplina Sistemas de Apoio à Decisão, UFBA). Decisão apoiada: **uma PME baiana deve instalar
um sistema fotovoltaico (microgeração, até 75 kWp)? Se sim, de que tamanho e com que forma de pagamento? Ou é melhor não instalar?**

- **Acesso:** https://sad-solar.onrender.com (plano gratuito: a 1ª requisição pode levar ~1 min para "acordar")
- **Credenciais:** crie uma conta na tela inicial (botão *Criar conta*) ou use um usuário de demonstração: `COMPLETAR_USUARIO` / `COMPLETAR_SENHA`
- **Vídeo de demonstração (3 a 5 min):** `COMPLETAR_LINK`
- **Repositório:** https://github.com/brunocer8/SAD

> Itens `COMPLETAR_*` precisam ser preenchidos por você antes de montar o PDF (usuário de demonstração e vídeo).

## Como executar

```bash
cd sad_solar
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload                                # abre em http://127.0.0.1:8000
```
O financiamento é **opcional**: o decisor informa a taxa (CET a.a.) na tela; sem ela, o sistema decide só com pagamento à vista (ver `docs/FUNDAMENTACAO.md`).
Opcional: `export GEMINI_API_KEY=...` habilita o texto explicativo por IA (sem a chave, o sistema usa um texto automático).
Testes: `pip install -r requirements-dev.txt && pytest -q` (39 testes).

## Arquitetura e fluxo de decisão

```mermaid
flowchart TD
    U[Decisor: município, consumo, tarifa, área, perfil diurno] --> API[app.py - FastAPI]
    D1[(dataset_ba_modelo.csv<br/>417 municípios x 12 meses)] --> R[REGRESSÃO<br/>geração específica kWh/kWp.dia<br/>f = ghi, fração difusa, temperatura]
    R --> F[financeiro.py<br/>balanço MENSAL, créditos FIFO 60 meses<br/>simultaneidade do autoconsumo<br/>fluxo de caixa 25 anos, VPL do projeto e do capital próprio]
    P[(parametros.py<br/>fonte / estimado / premissa)] --> F
    P --> MC[montecarlo.py<br/>SUMARIZAÇÃO: Monte Carlo<br/>percentis, prob. VPL>0]
    API --> DIM[dimensionar: kWp admissível<br/>potência <= 75 kWp e área do telhado]
    DIM --> F
    F --> ALT[Alternativas: 3 tamanhos x à vista/financiado]
    MC --> ALT
    ALT --> FILTRO{Filtro de viabilidade<br/>VPL > 0 e P(VPL>0) >= 50%}
    FILTRO -- reprovadas --> DESC[Descartadas, com motivo]
    FILTRO -- aprovadas + Não instalar --> SAW[SAW com pesos ROC]
    SAW --> SENS[Sensibilidade dos pesos<br/>+-30%, 1000 sorteios]
    SENS --> AGR[AGRUPAMENTO hierárquico<br/>do índice SAW]
    AGR --> REC[Recomendação final<br/>pode ser NÃO INSTALAR]
    REC --> UI[static/index.html: cartas, gráficos, relatório]
```

Funções analíticas (item 2 do enunciado), todas efetivamente executadas no fluxo acima:

| Função | Entrada | Processamento | Resultado decisório |
|---|---|---|---|
| Regressão | irradiação global, fração difusa, temperatura média (município x mês) | regressão linear múltipla (MQO) sobre a geração simulada com pvlib | geração mensal por kWp -> balanço de energia, economia, VPL |
| Sumarização | fluxos de caixa, 1.000 cenários de Monte Carlo por alternativa | VPL, TIR, payback, LCOE; percentis 10/50/90; probabilidade de VPL > 0 | filtro de viabilidade e critérios de risco do SAW |
| Agrupamento (perfis) | consumo, tarifa, fração diurna e razão geração/consumo de 6.000 cenários simulados de PME | k-means (k=4, `perfis.py`); o caso do usuário é atribuído ao centróide mais próximo | perfil do caso e taxa histórica de inviabilidade do grupo; vira ressalva no veredito |
| Agrupamento (alternativas) | índice SAW de cada alternativa | aglomerativo hierárquico (ligação completa), corte = raiz(2) x ruído do índice sob variação dos pesos | separa "mais recomendado" de "competitivas" e evita decidir por diferença insignificante |

O classificador (`python montecarlo.py treinar`) é um **experimento offline** e **não participa da recomendação**.

Documentação acadêmica: [`docs/FUNDAMENTACAO.md`](docs/FUNDAMENTACAO.md) (classificação da decisão, variáveis, fórmulas, referências, limitações) e
[`docs/caso_demonstracao.md`](docs/caso_demonstracao.md) (caso concreto e testes de estresse), [`docs/validacao_orcamentos.md`](docs/validacao_orcamentos.md) (comparação exploratória com estimativas comerciais), [`docs/DICIONARIO_DADOS.md`](docs/DICIONARIO_DADOS.md) e [`docs/RELATORIO_COMPLETO_SAD_SOLAR.md`](docs/RELATORIO_COMPLETO_SAD_SOLAR.md) (descrição técnica completa).

## Estrutura

| Arquivo | Papel |
|---|---|
| `financeiro.py` | geração, balanço mensal de créditos, fluxo de caixa, VPL/TIR/payback, dimensionamento |
| `montecarlo.py` | incerteza (Monte Carlo), análise de risco, experimento do classificador |
| `saw.py` | filtro de viabilidade, SAW/ROC, sensibilidade dos pesos, agrupamento, recomendação |
| `parametros.py` | todos os parâmetros, com tipo (fonte/estimado/premissa) e justificativa |
| `app.py`, `static/index.html` | API (login, simulação, relatórios) e interface |
| `tests/` | testes unitários e ponta a ponta (`pytest -q`) |
| `scripts/` | `validar_regressao.py` (validação por município), `caso_demonstracao.py` |

## Pendências do autor (não resolvidas pelo código)
- Preencher `COMPLETAR_USUARIO`, `COMPLETAR_SENHA` e `COMPLETAR_LINK` (usuário de demonstração e vídeo de 3 a 5 min); não foram inventados.
- Exportar o diagrama Mermaid como imagem para o PDF final (o PDF não renderiza o código).
- Confirmar em fontes oficiais: texto da Lei 14.300/2022 (potência em CA e Fio B), tarifa Coelba, taxas do BNB e do BB; completar edições e URLs com data de acesso nas referências.
- Orçamento real: informar o custo em R$/kWp no campo da tela; o valor é usado como custo fixo.
