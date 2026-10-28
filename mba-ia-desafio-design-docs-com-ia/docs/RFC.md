# RFC — Sistema de Webhooks de Notificação de Pedidos

| Campo | Valor |
| ----- | ----- |
| **Autor** | Gesiane Leal |
| **Status** | Em revisão |
| **Data** | 2026-10-28 |
| **Revisores** | Larissa (Tech Lead), Marcos (Product Manager), Bruno (Engenharia de Pedidos), Diego (Engenharia de Plataforma), Sofia (Engenharia de Segurança) |
| **Decisões relacionadas** | [ADR-001](adrs/ADR-001-outbox-no-mysql.md), [ADR-002](adrs/ADR-002-retry-backoff-e-dlq.md), [ADR-003](adrs/ADR-003-hmac-sha256-secret-por-endpoint.md), [ADR-004](adrs/ADR-004-at-least-once-x-event-id.md), [ADR-005](adrs/ADR-005-worker-processo-separado-polling.md), [ADR-006](adrs/ADR-006-reuso-dos-padroes-existentes.md), [ADR-007](adrs/ADR-007-uuid-e-snapshot-do-payload.md) |

## TL;DR

Propomos um sistema de **webhooks outbound** que notifica clientes B2B quando o status de seus
pedidos muda. A solução usa o **padrão outbox no MySQL existente** (nenhuma infraestrutura nova):
o evento é gravado na mesma transação SQL da mudança de status; um **worker em processo separado**
faz polling de 2 segundos e entrega via HTTP com **assinatura HMAC-SHA256** (secret por endpoint,
rotacionável). Entregas falhas seguem **retry com backoff exponencial (5 tentativas, ~15 h)** e caem
em uma **DLQ com replay administrativo**. A garantia é **at-least-once**, com deduplicação por
`X-Event-Id` do lado do cliente. Latência alvo: abaixo de 10 segundos.

## Contexto e problema

Três clientes B2B — Atlas Comercial, MaxDistribuição e Nova Cargo — pediram formalmente para serem
notificados em tempo real quando o status dos pedidos muda. Hoje eles fazem polling no
`GET /orders`, o que torna a integração lenta e cara para eles; a Atlas sinalizou risco de migração
para um concorrente caso a entrega não aconteça até o fim do trimestre ([09:00] Marcos).

O requisito de "tempo real" foi calibrado com os clientes: **qualquer entrega abaixo de 10 segundos
é aceitável** — o essencial é não deixar o cliente pendurado ([09:02] Marcos).

O contexto técnico é restritivo: a aplicação (OMS com máquina de estados de pedido, controle
transacional de estoque e auditoria) **não possui nenhum mecanismo de notificação, evento, fila ou
webhook**. A transação de mudança de status já é pesada (atualiza `orders`, insere
`order_status_history`, debita/recompõe estoque) e não pode ganhar dependências externas
([09:04] Bruno). Qualquer solução que insira I/O de rede na transação ou exija infraestrutura nova
está fora de cogitação para o time ([09:06]–[09:07] Diego).

## Proposta técnica (visão geral)

Cinco componentes, todos sobre a stack existente (Node.js + TypeScript + Prisma/MySQL):

1. **Configuração de webhooks (CRUD por customer)** — API REST autenticada para o cliente
   cadastrar/editar/remover webhooks (url, eventos de interesse), listar os webhooks de um customer
   e consultar o histórico de entregas. A secret é gerada pela plataforma e devolvida na criação;
   rotação self-service com grace period de 24 h ([09:31]–[09:34], [09:21]).
2. **Registro do evento (outbox)** — quando o status muda, uma linha em `webhook_outbox` é inserida
   **dentro da mesma transação SQL**, com o payload renderizado (snapshot) e `event_id` UUID.
   Commit ⇒ evento registrado; rollback ⇒ evento some junto. O filtro por eventos de interesse do
   cliente é aplicado **na inserção** ([09:06]–[09:08], [09:33]–[09:34], [09:51]–[09:52]).
3. **Worker de entrega (processo separado)** — polling a cada 2 segundos, batch pequeno, lê apenas
   pendentes e marca o resultado. O pior caso de latência inicial é ~2 s, dentro do requisito
   ([09:09]–[09:11]). Ordering implícita por `order_id` com single-worker (limitação conhecida)
   ([09:12]–[09:13]).
4. **Entrega assinada** — POST no endpoint do cliente com payload JSON enxuto (sem itens do pedido)
   e headers `X-Event-Id`, `X-Signature` (HMAC-SHA256 sobre o corpo), `X-Timestamp` e
   `X-Webhook-Id`; timeout de 10 s por tentativa; TLS obrigatório ([09:20]–[09:23], [09:42]–[09:44]).
5. **Resiliência** — retry com backoff exponencial (1 m / 5 m / 30 m / 2 h / 12 h; 5 tentativas) e
   DLQ em tabela separada com replay manual via endpoint administrativo (role `ADMIN`, com
   auditoria) ([09:15]–[09:18], [09:35]–[09:36]).

**O que não muda:** a transação de mudança de status permanece no MySQL e livre de I/O de rede; o
módulo de webhooks segue os padrões consolidados do projeto (módulos, erros `WEBHOOK_*`, Pino,
middleware de erro, schemas Zod) sem bibliotecas novas ([09:27]–[09:30]).

Detalhes de fluxo, contratos HTTP, matriz de erros e integração com o código existente ficam no
**FDD** — este RFC opera no nível de arquitetura e decisão.

## Alternativas consideradas

| Alternativa | Por que foi descartada | Trade-off |
| ----------- | ---------------------- | --------- |
| **Disparo síncrono no service de orders** ([09:03]–[09:06]) | Cliente lento travaria a mudança de status de outros pedidos; falha do cliente não pode reverter a mudança de status | Simplicidade aparente trocada por acoplamento do fluxo crítico a sistemas externos — inaceitável |
| **Redis Streams / fila externa** ([09:07]) | Exigiria subir infraestrutura nova ("overengineering" para o time pequeno) | Outbox no MySQL já existente resolve com latência de 2 s — suficiente para o requisito de 10 s |
| **Trigger no banco para reatividade** ([09:09]) | MySQL não tem listener nativo; trigger não notifica processo externo e exigiria improvisos | Polling de 2 s é mais simples e atende o requisito com folga |
| **Retry indefinido** ([09:15]) | Evento ficaria pendurado para sempre se o cliente sumir | Teto de 5 tentativas (~15 h) cobre indisponibilidades reais sem pendurar eternamente |
| **3 tentativas** ([09:16]) | Mataria entregas de clientes com indisponibilidade de algumas horas (caso real de manutenção de 2 h) | 5 tentativas cobrem janelas de até ~15 h |
| **DLQ como flag `failed` na própria outbox** ([09:18]) | Poluiria a leitura da outbox principal | Tabela separada dá leitura mais limpa e serve como evidência de debug/replay |
| **Secret global da plataforma** ([09:21]) | "Se vaza uma, vaza tudo" — um vazamento comprometeria todos os clientes | Secret por endpoint limita o impacto de vazamento ao cliente afetado |
| **Exactly-once** ([09:24]–[09:25]) | Exigiria coordenação dos dois lados; complexidade desproporcional | At-least-once + `X-Event-Id` segue o padrão de mercado (Stripe, GitHub) |

## Questões em aberto

1. **Rate limiting de saída** ([09:38]–[09:39]) — se o cliente tiver muitos pedidos mudando de
   status em pouco tempo, ele receberá uma chamada por evento. Decisão: **observar e decidir
   depois de medir o impacto** ("se virar problema, implementa"). Fica registrado como ponto de
   acompanhamento pós-lançamento.
2. **Arquivamento da outbox** ([09:08]) — linhas entregues crescem indefinidamente; citou-se
   "arquivar depois de 30 dias ou assim" como hipótese, mas a política está **fora do escopo desta
   feature** e será definida em fase futura.
3. **Escala horizontal e ordering global** ([09:13]) — ordenação garantida vale apenas por
   `order_id` e enquanto houver um único worker. Particionamento por `order_id` ou lock pessimista
   ficam como problema do futuro, caso a escala exija múltiplos workers.
4. **Notificação ativa de falhas** ([09:37]–[09:38]) — email de aviso ao cliente quando o webhook
   falha repetidamente ficou para uma próxima fase, depois de medir o impacto.

## Impacto e riscos

**Impacto:**
- `changeStatus` passa a registrar um evento adicional na transação (custo pequeno — mesma
  transação; ver FDD, seção de integração).
- Tabelas novas (configuração de webhooks, `webhook_outbox`, `webhook_dead_letter` e registro de
  entregas) e um novo processo a operar (worker).
- Operação ganha um procedimento manual novo (replay de DLQ), restrito a `ADMIN` e auditado.
- Estimativa de entrega: **3 sprints**, incluindo ≥ 2 dias úteis de revisão de segurança da Sofia
  antes do deploy ([09:45]–[09:47]).

**Riscos principais:**
- **Prazo (fim do trimestre)** — a Atlas pode migrar em caso de atraso ([09:00]); a estimativa de
  3 sprints foi validada na reunião ([09:47]).
- **Indisponibilidade longa do cliente** — eventos caem em DLQ após ~15 h e dependem de replay
  manual ([09:17]–[09:18]).
- **Crescimento da outbox** — mitigado por índices e batch pequeno; política de arquivamento em
  aberto ([09:08]).
- **Segurança** — HMAC e geração de secret têm revisão dedicada obrigatória antes do deploy
  ([09:46] Sofia).

## Decisões relacionadas

- [ADR-001: Padrão outbox no MySQL para registro de eventos de webhook](adrs/ADR-001-outbox-no-mysql.md)
- [ADR-002: Retry com backoff exponencial e DLQ persistida em tabela separada](adrs/ADR-002-retry-backoff-e-dlq.md)
- [ADR-003: Autenticação HMAC-SHA256 com secret por endpoint e rotação com grace period](adrs/ADR-003-hmac-sha256-secret-por-endpoint.md)
- [ADR-004: Garantia at-least-once com deduplicação por X-Event-Id](adrs/ADR-004-at-least-once-x-event-id.md)
- [ADR-005: Worker em processo separado com polling de 2 segundos](adrs/ADR-005-worker-processo-separado-polling.md)
- [ADR-006: Reuso máximo dos padrões e componentes existentes do projeto](adrs/ADR-006-reuso-dos-padroes-existentes.md)
- [ADR-007: UUIDs e snapshot do payload na inserção do evento na outbox](adrs/ADR-007-uuid-e-snapshot-do-payload.md)
