# Diagrama de funcionamento — Sol da Bahia

```mermaid
flowchart TD
    A[Usuário informa município, kWh/mês,<br/>tarifa, área útil, ligação e preferências] --> B{Cabe ao menos o sistema<br/>mínimo no telhado?}
    B -- Não --> C[Informar área insuficiente<br/>e pedir revisão técnica]
    B -- Sim --> D[Modelo de regressão:<br/>geração mensal por município]
    E[(Dados climáticos simulados<br/>417 cidades x 12 meses)] --> D
    D --> F[Simulação mensal de energia,<br/>créditos e economia]
    G[(Tarifas e premissas<br/>financeiras e regulatórias)] --> F
    F --> H[Sumarização:<br/>VPL, TIR, payback e Monte Carlo]
    H --> I{Filtro de viabilidade}
    I --> J[Ranking SAW:<br/>alternativas aprovadas + NÃO INSTALAR]
    J --> K[Agrupamento hierárquico +<br/>sensibilidade de pesos]
    K --> L[Recomendação explicada,<br/>gráficos e histórico]
```

Para incluir no PDF final, renderize esta imagem Mermaid em um editor compatível ou exporte o diagrama em PNG/SVG. A representação textual acima também pode ser usada para explicar o fluxo no vídeo.
