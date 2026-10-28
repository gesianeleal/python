# FDD — Sistema de Webhooks de Notificação de Pedidos

| Campo | Valor |
| ----- | ----- |
| **Autor** | Gesiane Leal |
| **Data** | 2026-10-28 |
| **Status** | Em revisão |
| **Documentos relacionados** | `docs/RFC.md`, `docs/PRD.md`, `docs/adrs/` |

## 1. Contexto e motivação técnica

A aplicação (OMS em Node.js + TypeScript, Prisma/MySQL) precisa notificar clientes B2B quando o
status de pedidos muda. O requisito de latência é abaixo de 10 segundos ([09:02]) e a transação de
mudança de status — `changeStatus` em `src/modules/orders/order.service.ts` — já executa updates em
`orders`, inserção em `order_status_history` e movimentação de estoque; ela **não pode** ganhar
chamadas HTTP ([09:04]).

A solução técnica está decidida e registrada nos ADRs: padrão outbox no MySQL
([ADR-001](adrs/ADR-001-outbox-no-mysql.md)), worker em processo separado com polling de 2 s
([ADR-005](adrs/ADR-005-worker-processo-separado-polling.md)), retry com backoff e DLQ
([ADR-002](adrs/ADR-002-retry-backoff-e-dlq.md)), entrega assinada com HMAC-SHA256
([ADR-003](adrs/ADR-003-hmac-sha256-secret-por-endpoint.md)), at-least-once com `X-Event-Id`
([ADR-004](adrs/ADR-004-at-least-once-x-event-id.md)) e reuso dos padrões existentes
([ADR-006](adrs/ADR-006-reuso-dos-padroes-existentes.md), [ADR-007](adrs/ADR-007-uuid-e-snapshot-do-payload.md)).
Este FDD detalha **como construir**.

## 2. Objetivos técnicos

1. Registrar cada mudança de status relevante na outbox, atomicamente com a transação do pedido
   ([09:06], [09:40]–[09:41]).
2. Entregar os eventos por HTTP abaixo de 10 s (polling de 2 s) ([09:09]–[09:10]).
3. Entregar com integridade e autenticidade verificáveis pelo cliente (HMAC-SHA256) ([09:20]–[09:22]).
4. Sobreviver a indisponibilidades dos clientes por até ~15 h (retry com backoff) ([09:15]–[09:17]).
5. Não perder eventos: falha permanente vai para DLQ consultável e reprocessável ([09:18], [09:35]–[09:36]).
6. Reusar módulos, erros, logger e padrões existentes, sem dependências novas ([09:27]–[09:30]).

## 3. Escopo e exclusões

**Incluso:** CRUD de configuração de webhooks; rotação de secret; enfileiramento transacional na
outbox; worker de entrega; assinatura HMAC; retry/backoff; DLQ + replay admin; histórico de
entregas; métricas/logs de acompanhamento.

**Exclusões** (espelham o PRD, seção "Fora de escopo"): email de aviso
([09:37]–[09:38]), rate limiting de saída ([09:38]–[09:39]), dashboard visual
([09:39]–[09:40]), arquivamento da outbox ([09:08]), webhooks inbound ([09:02]),
ordering global / múltiplos workers ([09:12]–[09:13]).

## 4. Fluxos detalhados

### 4.1 Criação do evento na outbox (transação do `changeStatus`)

Dentro do `this.prisma.$transaction` de `changeStatus` (`src/modules/orders/order.service.ts`),
após o update do pedido e a inserção do histórico, o service chama a função do módulo de webhooks:

```ts
await publishWebhookEvent(tx, order, from, to);
```

- `tx` é o `Prisma.TransactionClient` da transação corrente — a função é **pura em relação à
  infraestrutura**: só recebe o client e grava ([09:41] "função pura recebendo o tx").
- A função consulta os webhooks **ativos** do customer cujo filtro de eventos inclui `to`
  (o status de destino). **Se nenhum webhook do customer quer aquele status, nada é inserido**
  ([09:33]–[09:34]) — o filtro acontece **na inserção**, não no envio.
- Para **cada webhook interessado**, insere uma linha em `webhook_outbox` com: `id` (UUID),
  `event_id` (UUID — base do header `X-Event-Id`), `webhook_id`, `order_id`, `order_number`,
  `from_status`, `to_status`, `customer_id`, `total_cents`, **payload renderizado (snapshot)**
  ([09:51]–[09:52]), `status = PENDING`, `attempt_count = 0`, `created_at`.
- Se a inserção falhar, a exceção propaga e **a transação inteira dá rollback** — não existe caso
  de status mudar e evento não sair ([09:40]–[09:41]).

```
changeStatus (uma transação SQL)
├─ tx.order.update(status → to)
├─ tx.orderStatusHistory.create(...)
├─ débito/reposição de estoque (regras existentes)
└─ publishWebhookEvent(tx, order, from, to)
   ├─ webhooks ativos do customer com filtro contendo `to`  ──► nenhum? retorna sem inserir
   └─ INSERT webhook_outbox (PENDING, payload snapshot, event_id UUID)
```

### 4.2 Processamento pelo worker (polling de 2 s)

O worker (`src/worker.ts` + `webhook.processor.ts` no módulo, processo separado —
[09:11], [09:28]) roda um loop:

1. A cada **2 segundos** ([09:09]), busca os eventos **pendentes mais antigos**, em **batch
   pequeno** ([09:08]), ordenados por `created_at` — `WHERE status = PENDING AND next_attempt_at <= NOW()`.
2. Marca o lote como `PROCESSING` e, para cada evento, monta a requisição:
   `POST <url do webhook>` com o payload JSON, headers de identificação e a assinatura HMAC.
3. Aplica **timeout de 10 s** por chamada ([09:42]).
4. Em sucesso (HTTP 2xx): grava o registro de entrega e marca o evento como `DELIVERED`.
5. Em falha: incrementa `attempt_count`, calcula o próximo horário pelo backoff e volta a
   `PENDING`; na 5ª falha, move para a DLQ (4.3/4.4).

Estados do evento na outbox ([09:08]): `PENDING` → `PROCESSING` → `DELIVERED` | retorno a
`PENDING` (retry) | `FAILED` (falha permanente, movido para DLQ).

Com **um único worker**, eventos do mesmo `order_id` são processados na ordem de `created_at`
da outbox — ordering implícita por pedido. **Não há garantia de ordering global**
([09:12]–[09:13]).

### 4.3 Retry com backoff exponencial

Política ([09:15]–[09:17]): **5 tentativas** por evento, com progressão
**1 min → 5 min → 30 min → 2 h → 12 h** (≈ 15 h entre a primeira falha e a última tentativa).

- Falha = timeout, erro de rede ou resposta HTTP fora da faixa 2xx.
- O próximo disparo é agendado em `next_attempt_at = agora + intervalo_da_tentativa`.
- Cada tentativa usa o mesmo `event_id`; o cliente deduplica pelo `X-Event-Id`
  ([09:24]–[09:25]).
- A assinatura `X-Signature` é recalculada por tentativa (novo `X-Timestamp` de envio)
  ([09:44]).

### 4.4 DLQ e replay manual

- Esgotadas as 5 tentativas, o evento é considerado **falha permanente** e **movido** para
  `webhook_dead_letter`, com payload, motivo da falha e timestamp ([09:18]).
- **Replay manual**: `POST /api/v1/admin/webhooks/dead-letter/:id/replay` recoloca o evento na
  outbox como `PENDING` ([09:18]). Exige **role `ADMIN`** e a ação é **auditada** com o usuário
  que executou ([09:35]–[09:36]).
- O registro em DLQ permanece como evidência (payload, motivo, timestamps) para debug
  ([09:18]).

## 5. Contratos públicos

### 5.1 Payload do evento outbound e headers

Payload JSON da notificação (enviado ao endpoint do cliente — [09:43]):

```json
{
  "event_id": "8f14e45f-ceea-467f-a165-70867728950e",
  "event_type": "order.status_changed",
  "timestamp": "2026-10-28T14:32:10.482Z",
  "order_id": "0f8fad5b-d9cb-469f-a165-70867728950e",
  "order_number": "ORD-000042",
  "from_status": "PAID",
  "to_status": "PROCESSING",
  "customer_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "total_cents": 12990
}
```

> O payload **não inclui os itens do pedido** — para detalhes, o cliente consulta
> `GET /orders/:id` ([09:43]). Cada payload é um **snapshot** do estado no momento da mudança
> ([09:51]–[09:52]).

Headers enviados ([09:44]):

| Header | Conteúdo |
| ------ | -------- |
| `Content-Type` | `application/json` |
| `X-Event-Id` | UUID do evento (deduplicação no cliente) |
| `X-Webhook-Id` | id do cadastro de webhook (cliente com vários endpoints se localiza) |
| `X-Timestamp` | timestamp ISO 8601 do envio (permite ao cliente detectar replay) |
| `X-Signature` | assinatura **HMAC-SHA256 do corpo do request** com a secret do endpoint |

Verificação no lado do cliente (exemplo conceitual): `hmac_sha256(secret, raw_body) == X-Signature`.

### 5.2 Endpoints da API de configuração

Todos autenticados (JWT do sistema; `customer_id` no body/path — [09:32]); o replay exige `ADMIN`
([09:36]). Erros seguem o envelope padrão do projeto (`{ "error": { "code", "message", "details?" } }`).

#### 5.2.1 `POST /api/v1/webhooks` — cadastrar webhook ([09:31]–[09:32])

Request:
```json
{
  "customerId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "url": "https://integracao.atlas.example.com/webhooks/pedidos",
  "events": ["PAID", "SHIPPED", "DELIVERED"]
}
```
Response `201` (a **secret só aparece na criação**):
```json
{
  "id": "9c1e6b3a-...",
  "customerId": "3fa85f64-...",
  "url": "https://integracao.atlas.example.com/webhooks/pedidos",
  "events": ["PAID", "SHIPPED", "DELIVERED"],
  "active": true,
  "secret": "whsec_1f2e3d...",
  "createdAt": "2026-10-28T14:00:00.000Z"
}
```
Status codes: `201` criado; `400 WEBHOOK_INVALID_URL` (url `http`/inválida — [09:23]);
`400 WEBHOOK_EVENT_FILTER_INVALID` (lista vazia ou status desconhecido);
`401 UNAUTHORIZED`; `404 NOT_FOUND` (customer inexistente).

#### 5.2.2 `GET /api/v1/webhooks?customerId=...` — listar ([09:33])

Request: `GET /api/v1/webhooks?customerId=3fa85f64-5717-4562-b3fc-2c963f66afa6` — sem corpo (o filtro vai na query).

Response `200` (lista **sem secret**):
```json
{
  "data": [
    {
      "id": "9c1e6b3a-...",
      "url": "https://integracao.atlas.example.com/webhooks/pedidos",
      "events": ["PAID", "SHIPPED", "DELIVERED"],
      "active": true,
      "createdAt": "2026-10-28T14:00:00.000Z"
    }
  ]
}
```
Status codes: `200`; `401`; `404 NOT_FOUND` (customer inexistente).

#### 5.2.3 `PATCH /api/v1/webhooks/:id` — editar ([09:33])

Request (campos parciais):
```json
{ "events": ["SHIPPED", "DELIVERED"], "active": false }
```
Response `200`: mesmo formato do item da listagem, já atualizado.
Status codes: `200`; `400 WEBHOOK_INVALID_URL` / `WEBHOOK_EVENT_FILTER_INVALID`;
`404 WEBHOOK_NOT_FOUND`; `401`.

#### 5.2.4 `DELETE /api/v1/webhooks/:id` — remover ([09:33])

Request: `DELETE /api/v1/webhooks/9c1e6b3a-...` — sem corpo.

Response `204` (sem corpo). Status codes: `204`; `404 WEBHOOK_NOT_FOUND`; `401`.

#### 5.2.5 `POST /api/v1/webhooks/:id/secret/rotate` — rotacionar secret ([09:21])

Request: sem corpo (a rotação é disparada pelo próprio endpoint).

Response `200`:
```json
{
  "id": "9c1e6b3a-...",
  "secret": "whsec_9a8b7c...",
  "previousSecretExpiresAt": "2026-10-29T14:20:00.000Z"
}
```
> A secret **anterior permanece válida por 24 h** (`previousSecretExpiresAt`) para o cliente
> migrar; depois disso, é invalidada ([09:21]).

Status codes: `200`; `404 WEBHOOK_NOT_FOUND`; `422 WEBHOOK_SECRET_REQUIRED` (configuração sem
secret ativa — estado inconsistente); `401`.

#### 5.2.6 `GET /api/v1/webhooks/:id/deliveries` — histórico de entregas ([09:34])

Request: `GET /api/v1/webhooks/9c1e6b3a-.../deliveries?limit=100` — sem corpo.

Query: `?limit=100` (padrão e máximo 100 — "os últimos 100").

Response `200`:
```json
{
  "data": [
    {
      "id": "d1e2f3a4-...",
      "eventId": "8f14e45f-...",
      "toStatus": "PROCESSING",
      "status": "DELIVERED",
      "attempts": 1,
      "responseStatus": 200,
      "responseBody": "{\"received\":true}",
      "durationMs": 142,
      "createdAt": "2026-10-28T14:31:58.000Z",
      "deliveredAt": "2026-10-28T14:32:00.250Z"
    }
  ]
}
```
Status codes: `200`; `404 WEBHOOK_NOT_FOUND`; `401`.

#### 5.2.7 `POST /api/v1/admin/webhooks/dead-letter/:id/replay` — reprocessar DLQ ([09:18], [09:35]–[09:36])

Request: sem corpo.

Response `202`:
```json
{
  "id": "b7c8d9e0-...",
  "status": "PENDING",
  "replayedBy": "usr_2f1a..."
}
```
Status codes: `202` aceito; `403 FORBIDDEN` (sem role `ADMIN`); `404 WEBHOOK_NOT_FOUND`
(registro de DLQ inexistente); `409 CONFLICT` (registro já reprocessado e ainda pendente).
> A auditoria registra o usuário que executou o replay ([09:36]).

## 6. Matriz de erros previstos (`WEBHOOK_*`)

Todos os erros de API reutilizam `AppError` e o middleware central de erros; os códigos seguem o
prefixo `WEBHOOK_` decidido na reunião ([09:28]–[09:29]).

| Código | HTTP | Quando ocorre | Origem | Retriável? |
| ------ | ---- | ------------- | ------ | ---------- |
| `WEBHOOK_NOT_FOUND` | 404 | Webhook (ou registro de DLQ) inexistente na operação | API | Não |
| `WEBHOOK_INVALID_URL` | 400 | URL não é `https` válida no cadastro/edição ([09:23]) | API | Não |
| `WEBHOOK_EVENT_FILTER_INVALID` | 400 | Lista de eventos vazia ou contém status desconhecido | API | Não |
| `WEBHOOK_SECRET_REQUIRED` | 422 | Operação de assinatura/rotação sem secret ativa (estado inconsistente) | API | Não |
| `WEBHOOK_PAYLOAD_TOO_LARGE` | 422 | Payload do evento excede 64 KB — entrega recusada, sem truncar ([09:23]–[09:24]) | Worker | Não |
| `WEBHOOK_DELIVERY_TIMEOUT` | — | Cliente não respondeu em 10 s ([09:42]) | Worker | Sim (retry) |
| `WEBHOOK_DELIVERY_FAILED` | — | Resposta HTTP fora da faixa 2xx | Worker | Sim (retry) |
| `WEBHOOK_MAX_ATTEMPTS_EXCEEDED` | — | 5 tentativas esgotadas → evento movido para DLQ ([09:15]–[09:18]) | Worker | Não (apenas replay manual) |

> Erros de entrega (origem Worker) não são respostas HTTP da API: aparecem no registro de
> entregas (5.2.6) e no motivo da DLQ. A mensagem carrega o `webhook_id`/`event_id` para
> correlação.

## 7. Estratégias de resiliência

| Mecanismo | Definição | Fonte |
| --------- | --------- | ----- |
| Atomicidade do evento | Inserção na outbox dentro da transação do `changeStatus`; rollback remove o evento | [09:40]–[09:41] |
| Timeout de entrega | 10 s por chamada; excedeu = falha | [09:42] |
| Retry | 5 tentativas com backoff 1 m/5 m/30 m/2 h/12 h | [09:15]–[09:17] |
| DLQ | Falha permanente em tabela separada, com payload/motivo/timestamps | [09:18] |
| Replay | Recolocação manual como `PENDING` via endpoint admin (auditado) | [09:18], [09:36] |
| Idempotência no cliente | At-least-once + dedup por `X-Event-Id` | [09:24]–[09:25] |
| Snapshot imutável | Payload renderizado na inserção; retries entregam o mesmo conteúdo | [09:51]–[09:52] |
| Limite de payload | 64 KB; acima disso, erro (sem truncamento) | [09:23]–[09:24] |
| TLS | URL obrigatoriamente `https` | [09:23] |

## 8. Observabilidade

**Métricas** (instrumentação proposta — o projeto hoje não possui stack de métricas; a coleta pode
começar por contadores emitidos pelo worker com o logger):
- `webhook_events_enqueued_total` — eventos enfileirados na outbox (por status de destino).
- `webhook_deliveries_total{result=success|failure}` — entregas por resultado.
- `webhook_delivery_duration_ms` — latência de entrega (histograma/percentis, base do PRD-MET-01).
- `webhook_outbox_pending` / idade do pendente mais antigo — saúde do processamento
  ([09:08]).
- `webhook_dead_letter_size` — tamanho da DLQ (indicador de problema sistêmico no cliente)
  ([09:18]).

**Logs** (Pino, `src/shared/logger/index.ts`, com a redaction já configurada — [09:29]):
- Enfileiramento: `event_id`, `webhook_id`, `order_id`, `from_status → to_status`.
- Tentativa de entrega: `event_id`, `attempt`, `durationMs`, `responseStatus` (ou motivo da falha).
- Movimentação para DLQ: `event_id`, `attempts`, motivo.
- Replay: registro de **auditoria** com o usuário que executou ([09:36]).
- Nenhuma secret em log (redaction existente cobre tokens; secrets usam nomes dedicados para
  redaction).

**Tracing** (correlação): o `event_id`/`X-Event-Id` funciona como identificador de correlação
ponta a ponta — do enfileiramento (transação do pedido) à entrega e à DLQ, permitindo reconstruir
a jornada de um evento pelos logs. O middleware de request já injeta um `requestId` nas operações
de API; o worker registra o `event_id` em todas as linhas de log. (O projeto não possui APM;
uma integração de tracing distribuído fica como evolução futura — detalhe de instrumentação, não
uma decisão da reunião.)

## 9. Dependências e compatibilidade

- **Stack**: Node.js ≥ 20, TypeScript, Express, Prisma 5/MySQL, Zod, Pino, Vitest — tudo já
  presente no projeto ([09:29]–[09:30]).
- **Bibliotecas novas**: nenhuma ([09:30]).
- **Compatibilidade**: HMAC-SHA256 é padrão de mercado, disponível em qualquer linguagem
  ("todo cliente sério tem biblioteca" — [09:20]).
- **Configuração nova** (padrão `src/config/env.ts`): intervalo de polling e teto de tentativas
  parametrizáveis (defaults: 2 s e 5) — detalhe de implementação para testes do worker.

## 10. Critérios de aceite técnicos

| ID | Critério |
| -- | -------- |
| FDD-CA-01 | Mudança de status commitada grava evento na outbox **na mesma transação**; rollback não deixa evento órfão ([09:06], [09:41]) |
| FDD-CA-02 | Eventos filtrados na inserção: nenhum webhook interessado ⇒ nenhuma linha na outbox ([09:34]) |
| FDD-CA-03 | Entrega abaixo de 10 s no cenário local (polling de 2 s + entrega) ([09:10]) |
| FDD-CA-04 | Retry respeita 5 tentativas na progressão 1 m/5 m/30 m/2 h/12 h ([09:17]) |
| FDD-CA-05 | Após a 5ª falha, o evento está na DLQ com payload e motivo; replay recoloca como `PENDING` ([09:18]) |
| FDD-CA-06 | Assinatura `X-Signature` verifica com HMAC-SHA256 sobre o corpo ([09:20]–[09:22]) |
| FDD-CA-07 | URL `http` recusada; payload > 64 KB recusado ([09:23]–[09:24]) |
| FDD-CA-08 | Rotação de secret: antiga válida por 24 h ([09:21]) |
| FDD-CA-09 | Replay exige `ADMIN` e registra auditoria ([09:36]) |
| FDD-CA-10 | Ordering por `order_id` com worker único (limitação documentada) ([09:12]–[09:13]) |

## 11. Riscos e mitigação (técnicos)

| Risco | Mitigação |
| ----- | --------- |
| Worker parado acumula eventos e degrada a latência | Monitorar `webhook_outbox_pending` e idade do pendente mais antigo (seção 8); worker é processo próprio com restart independente ([09:11]) |
| Evento maior que o limite | Erro `WEBHOOK_PAYLOAD_TOO_LARGE` na entrega, registrado no histórico ([09:24]) |
| Cliente sem deduplicação processa evento duplicado | Documentação destacada no portal ([09:26]) |
| Secret comprometida | Rotação com grace period de 24 h ([09:21]); revisão de segurança dedicada antes do deploy ([09:46]) |
| Transação maior pelo enqueue | Inserção única e simples (uma linha por webhook interessado), no mesmo banco, sem I/O externo ([09:41]) |

## 12. Integração com o sistema existente

> Seção obrigatória do desafio. Os caminhos abaixo existem no repositório e foram conferidos
> contra o código-fonte da aplicação base.

1. **`src/modules/orders/order.service.ts` — método `changeStatus`** (l. 126–179).
   É o ponto de integração central: após `tx.order.update` e `tx.orderStatusHistory.create`,
   o método passa a chamar `publishWebhookEvent(tx, order, from, to)`, recebendo o
   `Prisma.TransactionClient` da própria transação. Qualquer falha na inserção da outbox
   derruba a transação inteira — mantendo a garantia "status mudou ⇔ evento registrado"
   ([09:40]–[09:41]). Nenhuma chamada HTTP acontece dentro da transação ([09:04]).

2. **`src/modules/orders/order.status.ts` — máquina de estados** (`canTransition`, enum
   `OrderStatus`). A lista de eventos de um webhook (`events`) é validada contra os status
   notificáveis do domínio, e o enfileiramento só ocorre para transições válidas — o mesmo
   módulo que governa as transições de pedido governa os eventos ([09:34], [09:51]).

3. **`src/shared/errors/app-error.ts` + `src/shared/errors/http-errors.ts`** (exportados em
   `src/shared/errors/index.ts`). As novas classes (`WEBHOOK_NOT_FOUND`, `WEBHOOK_INVALID_URL`,
   `WEBHOOK_SECRET_REQUIRED`, ...) seguem exatamente o padrão das classes existentes
   (`AppError` base com `statusCode` + `errorCode` + `details`, como `InvalidStatusTransitionError`
   e `InsufficientStockError`) ([09:28]–[09:29]).

4. **`src/middlewares/error.middleware.ts` — tratamento centralizado.** Sem mudanças: o middleware
   já serializa `AppError` (código, mensagem, detalhes), validações Zod e erros Prisma — os erros
   do módulo de webhooks são tratados automaticamente no formato padrão da API ([09:29]).

5. **`src/middlewares/auth.middleware.ts` — `authenticate` e `requireRole`.** As rotas do módulo
   usam `authenticate`; o endpoint de replay usa `requireRole('ADMIN')`, reaproveitando a função
   existente ([09:36]).

6. **`src/routes/index.ts` + `src/app.ts` — composição da aplicação.** O módulo é registrado como
   os demais: `buildWebhookRouter` entra em `buildApiRouter` (rota `/webhooks`) e
   `WebhookRepository`/`WebhookService`/`WebhookController` são instanciados em
   `buildControllers` ([09:27]).

7. **`src/server.ts` — padrão de entry point.** O novo `src/worker.ts` replica o estilo
   (bootstrap, logger, `prisma.$disconnect` no shutdown, handlers de sinal) e ganha um script
   `worker` no `package.json`, como os scripts existentes ([09:11]).

8. **`prisma/schema.prisma` (+ `prisma/migrations/`).** Novos modelos seguindo as convenções do
   schema: UUID (`@id @default(uuid()) @db.Char(36)`), `@@map` em snake_case, índices explícitos
   ([09:08], [09:51]):
   - `WebhookEndpoint` (`webhook_endpoints`): `url`, `secret` (ativa), `previousSecret`,
     `previousSecretExpiresAt`, `events`, `active`, `customerId`;
   - `WebhookOutbox` (`webhook_outbox`): `eventId`, `webhookId`, `payload` (snapshot),
     `status`, `attemptCount`, `nextAttemptAt`, `createdAt` — índice em `(status, nextAttemptAt)`
     ([09:08]);
   - `WebhookDeadLetter` (`webhook_dead_letter`): payload, motivo, timestamps ([09:18]);
   - `WebhookDelivery` (`webhook_deliveries`): histórico para o endpoint de consulta do cliente
     (status, response, duração, tentativas) — suporte ao requisito de histórico de entregas
     (PRD-FR-06, [09:34]).

9. **`src/config/database.ts` + `src/config/env.ts`.** O worker cria instância própria de
   `PrismaClient` sobre o mesmo banco (client é por processo — [09:29]–[09:30]); variáveis novas
   (ex.: `WEBHOOK_POLL_INTERVAL_MS`, `WEBHOOK_MAX_ATTEMPTS`) seguem o schema Zod existente.

10. **`src/shared/logger/index.ts`.** O worker usa o mesmo logger Pino com redaction
    ([09:29]); nenhuma biblioteca nova de logging entra no projeto.

## 13. Referências

- `docs/RFC.md`, `docs/PRD.md`, `docs/adrs/ADR-001` … `ADR-007`
- `TRANSCRICAO.md` (fonte primária de todas as decisões citadas)
