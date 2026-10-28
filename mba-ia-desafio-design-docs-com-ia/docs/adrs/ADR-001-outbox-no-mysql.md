# ADR-001: Padrão outbox no MySQL para registro de eventos de webhook

- **Status:** Aceito
- **Data:** 2026-10-28
- **Decisores:** Larissa (Tech Lead), Diego (Engenharia de Plataforma), Bruno (Engenharia de Pedidos)
- **Fonte primária:** `TRANSCRICAO.md` — [09:03]–[09:08]

## Contexto

A aplicação é um Order Management System (OMS) em produção, com máquina de estados de pedido
controlada, controle transacional de estoque e auditoria de mudanças de status. Ela **não possui
nenhum mecanismo de notificação externa** — sem eventos, filas ou webhooks. A feature discutida
precisa notificar clientes B2B em tempo real (abaixo de 10 segundos) quando o status dos pedidos muda.

A operação crítica é o método `changeStatus` (em `src/modules/orders/order.service.ts`), cuja
transação já é pesada: atualiza `orders`, insere em `order_status_history` e debita/recompõe
`stock_quantity` dos produtos. Um disparo síncrono de HTTP no meio dessa transação faria com que
qualquer cliente lento travasse a mudança de status de outros pedidos e tornaria impossível dar
rollback na mudança de status por falha do cliente ([09:04] Bruno).

## Decisão

Adotar o **padrão outbox no MySQL existente**: dentro da mesma transação SQL que atualiza o pedido
e o histórico, inserir uma linha em uma tabela `webhook_outbox` representando o evento. Um worker
separado lê essa tabela e dispara as chamadas HTTP.

- Commit da transação ⇒ evento registrado; rollback ⇒ evento some junto (sem inconsistência) ([09:06] Diego).
- A tabela tem índice no campo de status (`pendente`, `processando`, `falhou`, `entregue`) e em
  `created_at`; o worker lê apenas pendentes, em batch pequeno, e marca como entregue ([09:08]).
- Arquivamento das linhas entregues (ex.: após 30 dias) fica **fora do escopo desta feature** ([09:08]).
- Nenhuma infraestrutura nova é necessária ([09:07]).

## Alternativas consideradas

1. **Disparo síncrono no service de orders** — descartada em [09:03]–[09:06]:
   qualquer cliente lento travaria a transação de mudança de status; se o cliente estivesse fora
   do ar, não haveria como dar rollback na mudança de status.
2. **Redis Streams (ou fila externa)** — descartada em [09:07]:
   exigiria subir infraestrutura adicional ("subir Redis Cluster pra isso é overengineering" —
   de um time pequeno); o MySQL já existente resolve.
3. **Trigger de banco para reatividade imediata** — descartada em [09:09]:
   o MySQL não possui listener nativo como o `NOTIFY/LISTEN` do PostgreSQL; a trigger apenas
   executa SQL e não notifica processo externo — avisar o worker exigiria improvisos (escrever em
   arquivo, bater em endpoint).

## Consequências

**Positivas:**
- Atomicidade garantida entre a mudança de status e o evento: não existe estado em que o status
  mudou e o evento não saiu ([09:07], [09:41]).
- Zero infraestrutura nova: reaproveita MySQL, Prisma e a stack do time.
- A transação principal permanece livre de dependências externas.

**Negativas / trade-offs:**
- Latência mínima de ~2 segundos na entrega, decorrente da leitura por polling ([09:08]–[09:10]).
- A tabela cresce indefinidamente sem rotina de arquivamento — problema aceito e adiado ([09:08]).
- Adiciona carga de leitura concorrente ao banco principal (mitigada por índices e batch pequeno).
