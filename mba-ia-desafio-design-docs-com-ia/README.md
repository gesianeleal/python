# Sistema de Webhooks de Notificação de Pedidos — Pacote de Design Docs

> Desafio técnico do MBA em Engenharia de Software com IA (Full Cycle). Este repositório é um
> fork do [repositório base do desafio](https://github.com/devfullcycle/mba-ia-desafio-design-docs-com-ia),
> que contém a aplicação (OMS), a transcrição da reunião técnica (`TRANSCRICAO.md`) e a estrutura
> de pastas preenchida por este trabalho: `docs/PRD.md`, `docs/RFC.md`, `docs/FDD.md`,
> `docs/TRACKER.md` e `docs/adrs/`.

## Sobre o desafio

O desafio parte de um cenário comum (e desconfortável) do dia a dia de engenharia: uma feature
importante foi decidida em uma reunião técnica de ~55 minutos entre tech lead, PM, engenheiros e
segurança, mas nada foi registrado além da transcrição literal da call. Minha tarefa foi
transformar essa transcrição + o código existente da aplicação em um **pacote completo de design
docs** — PRD, RFC, FDD, ADRs, Tracker de rastreabilidade e este README — usando IA como ferramenta
principal de produção, no papel de maestro: definir o que produzir, escrever bons prompts, revisar
criticamente cada geração e corrigir até o resultado ficar consistente.

O resultado é a documentação da feature **Sistema de Webhooks de Notificação de Pedidos**: CRUD de
configuração de webhooks por cliente, registro transacional de eventos em outbox, worker de entrega
com polling e retry, assinatura HMAC-SHA256 com secret por endpoint, DLQ com replay administrativo
e histórico de entregas — tudo rastreável à transcrição ou ao código, sem requisito inventado.

## Ferramentas de IA utilizadas

- **Agente de IA com acesso direto ao repositório (Hermes Agent)** — ferramenta principal de
  produção. Papéis: (1) ler o código-fonte e a transcrição completa; (2) extrair o inventário
  estruturado de decisões/requisitos/descartes com timestamps; (3) gerar os rascunhos de cada
  documento a partir de prompts dirigidos (ver seção de prompts); (4) executar uma auditoria cética
  contra as fontes, apontando itens sem origem, contradições e caminhos inválidos; (5) apoiar a
  correção dos problemas encontrados.
- **Script de validação próprio (Python, `~/…/valida_mba3.py`, não versionado)** — verificação
  automatizada da checklist do desafio: presença das seções obrigatórias, contagens mínimas
  (RFs, ADRs, endpoints, códigos de erro), formato da tabela do tracker, cruzamento dos 98
  timestamps `[hh:mm] Nome` do tracker contra a transcrição e checagem de que todo caminho de
  código citado existe no repositório (`git ls-files`).
- **Revisão humana (autora)** — decisões de escopo, critério de qualidade e revisão final item a
  item da checklist antes do push.

## Workflow adotado

1. **Contextualização (ciclo 1)** — o agente leu a `TRANSCRICAO.md` (155 linhas com timestamp:
   151 falas nominais de 5 participantes + 4 rubricas de cena) e o código da aplicação
   (`src/`, `prisma/`, `tests/`), produzindo um **inventário estruturado**: decisões fechadas,
   requisitos funcionais, restrições, alternativas descartadas, itens adiados e ganchos no
   código — sempre com timestamp.
2. **ADRs primeiro (ciclo 2)** — as decisões formam o esqueleto do "como implementar": produzi as
   7 decisões como ADRs em MADR (6 principais da reunião + 1 secundária de modelagem), com
   alternativas reais e trade-offs explícitos.
3. **RFC → FDD → PRD (ciclo 3)** — com as decisões formalizadas, consolidei a proposta técnica
   (RFC), detalhei a implementação (FDD, incluindo a seção obrigatória de integração com o código)
   e produzi o PRD por último, como consolidação de produto.
4. **Tracker + auditoria (ciclo 4)** — montei o tracker varrendo os documentos prontos e rodei a
   auditoria cética (prompt 3) + o script de validação para provar a rastreabilidade.
5. **README e revisão final (ciclo 5)** — documentei o processo (este arquivo) e passei a checklist
   de critérios de aceite item a item.

Regra transversal: **nada entra nos documentos sem fonte** — timestamp da transcrição ou caminho
de arquivo real do código. O tracker é o mecanismo que comprova isso.

## Prompts customizados

Os prompts abaixo são a espinha dorsal do processo (foram adaptados durante o trabalho):

**Prompt 1 — Extração estruturada da transcrição (filtra o que entra e o que NÃO entra):**

```text
Você vai analisar a transcrição de uma reunião técnica (TRANSCRICAO.md) para um projeto de
Sistema de Webhooks de Notificação de Pedidos. Produza um inventário em markdown:
1) Decisões FECHADAS: cada uma com decisão, participantes, timestamp [hh:mm] Nome e frase-chave.
2) Requisitos funcionais explícitos (≥ 8 candidatos), com timestamp.
3) Restrições e requisitos não funcionais, com timestamp.
4) Alternativas EXPLICITAMENTE descartadas e o motivo, com timestamp.
5) Itens adiados, fora de escopo ou deixados em aberto, com timestamp.
6) Menções a arquivos/módulos/classes/padrões do código existente.
Regras: use SOMENTE o que está na transcrição; não complete lacunas; não reformule decisões;
marque com "(?)" qualquer item ambíguo. Não inclua nada sem timestamp.
```

**Prompt 2 — Geração de ADR no formato MADR:**

```text
Com base no item "<decisão>" do inventário (fonte: transcrição [hh:mm] Nome + código),
escreva um ADR em MADR com: Status (Aceito), Contexto, Decisão, Alternativas Consideradas
(≥ 1 alternativa REALMENTE discutida, com o trade-off do descarte e timestamp) e Consequências
(positivas e negativas/trade-offs explícitos). Não invente contexto não discutido; se um
detalhe não estiver na fonte, não o inclua. Código citado deve existir no repositório.
```

**Prompt 3 — Auditoria cética anti-alucinação (rodado entre as gerações):**

```text
Você é um revisor cético. Compare os documentos gerados (PRD/RFC/FDD/ADRs) contra as fontes
(TRANSCRICAO.md e o código). Liste TODOS os itens sem origem identificável, citações de
arquivos inexistentes, itens descartados na reunião que reapareceram como requisito, e
contradições entre documentos. Formato: "| item | arquivo | problema | correção sugerida |".
Não elogie; só aponte problemas verificáveis.
```

**Prompt 4 — Contratos HTTP do FDD (extração dirigida de endpoints):**

```text
Extraia da transcrição TODOS os endpoints discutidos (CRUD de configuração, rotação de secret,
deliveries, replay admin). Para cada um, gere: método e path, descrição de uma linha, request
de exemplo (JSON), response 2xx de exemplo (JSON) e status codes de erro esperados (com
códigos WEBHOOK_* alinhados à matriz de erros). Use os headers e o payload do evento
exatamente como definidos na reunião ([09:43]–[09:44]). Marque com "[proposta]" qualquer
detalhe que você esteja completando por convenção, não por fonte.
```

## Iterações e ajustes

O processo levou **5 ciclos principais** de geração → revisão crítica → correção. Os ajustes
concretos mais relevantes:

1. **Requisito corrigido dentro da própria reunião (ciclo 1).** A fala [09:31] sugeria
   "customer_id implícito do JWT"; a própria reunião se corrigiu em [09:32] ("o customer_id é
   passado no body ou no path; não vem do JWT"). Na extração, mantive apenas a versão corrigida —
   sem isso, PRD e FDD propagariam um requisito errado (e o tracker não teria como defender a
   origem).
2. **Contratos do FDD incompletos (ciclo 4).** Na primeira versão, os endpoints de GET, DELETE e
   de ações (rotate/replay) não tinham bloco de request explícito — o critério do desafio exige
   ≥ 4 endpoints com exemplos de request e response. A auditoria apontou e padronizei: todos os
   7 endpoints ganharam `Request:` (corpo de exemplo ou "sem corpo" explícito) e `Response:` com
   payload e status codes.
3. **Contradição entre documentos (ciclo 4).** O RFC dizia "duas tabelas novas" enquanto o FDD
   detalhava quatro estruturas novas (configuração de webhooks, outbox, DLQ e registro de
   entregas). Corrigi o RFC para refletir o detalhamento do FDD — coerência entre alturas
   (arquitetura × implementação).
4. **Caminhos "a criar" confundidos com existentes (ciclo 4).** A validação de caminhos de código
   (`git ls-files`) mostrou que `src/worker.ts` e `src/modules/webhooks` não existem — são
   proposta. Marquei explicitamente como "novo"/"a criar" (FDD e ADRs), e confirmei que os 10
   caminhos de integração citados existem de fato no repositório.
5. **Itens descartados sendo "pescados" de volta (ciclos 3–4).** Email de aviso, dashboard, rate
   limiting, webhooks inbound e ordering global são exclusões explícitas da reunião. Rodei
   verificações dirigidas (grep) para garantir que aparecem **somente** em contexto de exclusão/
   questão em aberto — nunca como requisito.
6. **Rastreabilidade provada por script (ciclo 4).** O validador cruzou as 98 linhas
   `TRANSCRICAO` do tracker contra a transcrição (todos os pares `[hh:mm] Nome` existem; 0
   divergências) e conferiu as contagens dos critérios (7 ADRs, 10 RFs, 7 endpoints, 8 códigos
   `WEBHOOK_*`, 10 caminhos de integração).

## Como navegar a entrega

Ordem de leitura sugerida (do "por quê" ao "como construir"):

1. [`docs/PRD.md`](docs/PRD.md) — o produto: problema, público, escopo (incl. o que ficou de
   fora), requisitos, métricas, riscos.
2. [`docs/RFC.md`](docs/RFC.md) — a proposta técnica para revisão: abordagem, alternativas
   descartadas com trade-offs e questões em aberto.
3. [`docs/adrs/`](docs/adrs/) — as 7 decisões, uma a uma (MADR): **ADR-001** outbox no MySQL ·
   **ADR-002** retry/backoff/DLQ · **ADR-003** HMAC-SHA256 secret por endpoint · **ADR-004**
   at-least-once com `X-Event-Id` · **ADR-005** worker separado com polling · **ADR-006** reuso
   dos padrões do projeto · **ADR-007** UUID e snapshot do payload.
4. [`docs/FDD.md`](docs/FDD.md) — a implementação em detalhe: fluxos, contratos HTTP, matriz de
   erros `WEBHOOK_*`, resiliência, observabilidade e a integração com o código existente.
5. [`docs/TRACKER.md`](docs/TRACKER.md) — a rastreabilidade de cada item à transcrição ou ao
   código (108 linhas; 90,7% com timestamp da reunião).

```
.
├── README.md          ← este arquivo (processo de produção)
├── TRANSCRICAO.md     ← fonte primária (não alterado)
├── docs/
│   ├── PRD.md  RFC.md  FDD.md  TRACKER.md
│   └── adrs/ADR-001-… … ADR-007-…
└── src/ prisma/ tests/  ← aplicação (não alterada; contexto e referência)
```

## Integridade do código

A entrega é puramente documental: `src/`, `prisma/`, `tests/`, `TRANSCRICAO.md` e as configurações
do repositório base **não foram alterados** — a diferença em relação ao repositório base são apenas
este `README.md` e os arquivos em `docs/` (verificável com `git diff` contra o upstream).
