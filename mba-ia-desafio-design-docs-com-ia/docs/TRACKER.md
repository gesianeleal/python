# Tracker de Rastreabilidade

Este tracker mapeia **cada item registrado nos documentos** (`docs/PRD.md`, `docs/RFC.md`,
`docs/FDD.md` e `docs/adrs/*`) à sua origem: a transcrição da reunião (`TRANSCRICAO.md`) ou o
código-fonte da aplicação. Ele é a defesa contra alucinação: nenhum item sem "Localização"
preenchível deveria estar nos documentos.

- **Fonte `TRANSCRICAO`** → coluna Localização no formato `[hh:mm] Nome` (falante da reunião).
- **Fonte `CODIGO`** → coluna Localização com o caminho real do arquivo no repositório.
- Cobertura: todos os itens identificáveis dos documentos estão listados abaixo (108 linhas).

| ID | Documento | Tipo | Conteúdo (resumo) | Fonte | Localização |
| -- | --------- | ---- | ----------------- | ----- | ----------- |
| PRD-MET-01 | docs/PRD.md | Objetivo/Métrica | Entrega < 10 s para ≥ 95% dos eventos (p95) | TRANSCRICAO | [09:02] Marcos |
| PRD-MET-02 | docs/PRD.md | Objetivo/Métrica | 100% das mudanças de status commitadas geram evento na outbox | TRANSCRICAO | [09:06] Diego |
| PRD-MET-03 | docs/PRD.md | Objetivo/Métrica | 3 clientes B2B (Atlas, MaxDistribuição, Nova Cargo) integrados | TRANSCRICAO | [09:00] Marcos |
| PRD-MET-04 | docs/PRD.md | Objetivo/Métrica | Janela de retry de até ~15 h antes da DLQ | TRANSCRICAO | [09:17] Diego |
| PRD-OUT-01 | docs/PRD.md | Fora de escopo | Email de aviso ao cliente — adiado para próxima fase | TRANSCRICAO | [09:37] Larissa |
| PRD-OUT-02 | docs/PRD.md | Fora de escopo | Rate limiting de saída — observar e decidir depois | TRANSCRICAO | [09:39] Larissa |
| PRD-OUT-03 | docs/PRD.md | Fora de escopo | Dashboard visual — projeto separado do time de frontend | TRANSCRICAO | [09:40] Larissa |
| PRD-OUT-04 | docs/PRD.md | Fora de escopo | Arquivamento das linhas entregues da outbox | TRANSCRICAO | [09:08] Diego |
| PRD-OUT-05 | docs/PRD.md | Fora de escopo | Webhooks inbound (cliente → plataforma) | TRANSCRICAO | [09:02] Marcos |
| PRD-OUT-06 | docs/PRD.md | Fora de escopo | Ordering global / múltiplos workers | TRANSCRICAO | [09:13] Diego |
| PRD-FR-01 | docs/PRD.md | Requisito Funcional | Cadastrar webhook (url + eventos); secret gerada e devolvida na criação; customer_id no body | TRANSCRICAO | [09:31] Marcos |
| PRD-FR-02 | docs/PRD.md | Requisito Funcional | Listar webhooks de um customer | TRANSCRICAO | [09:33] Bruno |
| PRD-FR-03 | docs/PRD.md | Requisito Funcional | Editar webhook (PATCH) | TRANSCRICAO | [09:33] Bruno |
| PRD-FR-04 | docs/PRD.md | Requisito Funcional | Remover webhook (DELETE) | TRANSCRICAO | [09:33] Bruno |
| PRD-FR-05 | docs/PRD.md | Requisito Funcional | Filtro de eventos aplicado na inserção da outbox | TRANSCRICAO | [09:34] Bruno |
| PRD-FR-06 | docs/PRD.md | Requisito Funcional | Histórico de entregas — últimos 100 com payload/response/tempo | TRANSCRICAO | [09:34] Marcos |
| PRD-FR-07 | docs/PRD.md | Requisito Funcional | Replay manual de DLQ (endpoint admin; role ADMIN; auditoria) | TRANSCRICAO | [09:18] Diego |
| PRD-FR-08 | docs/PRD.md | Requisito Funcional | Rotação de secret com grace period de 24 h | TRANSCRICAO | [09:21] Sofia |
| PRD-FR-09 | docs/PRD.md | Requisito Funcional | Notificação outbound order.status_changed em < 10 s | TRANSCRICAO | [09:02] Marcos |
| PRD-FR-10 | docs/PRD.md | Requisito Funcional | Entrega assinada (HMAC) com headers X-Event-Id/X-Webhook-Id/X-Timestamp | TRANSCRICAO | [09:44] Diego |
| PRD-RNF-01 | docs/PRD.md | Requisito Não Funcional | Latência de entrega < 10 s (polling de 2 s) | TRANSCRICAO | [09:10] Larissa |
| PRD-RNF-02 | docs/PRD.md | Requisito Não Funcional | URL obrigatoriamente HTTPS (http recusado) | TRANSCRICAO | [09:23] Sofia |
| PRD-RNF-03 | docs/PRD.md | Requisito Não Funcional | Limite de payload de 64 KB (erro acima; sem truncar) | TRANSCRICAO | [09:24] Larissa |
| PRD-RNF-04 | docs/PRD.md | Requisito Não Funcional | Timeout de 10 s por chamada de entrega | TRANSCRICAO | [09:42] Diego |
| PRD-RNF-05 | docs/PRD.md | Requisito Não Funcional | Garantia at-least-once (dedup por X-Event-Id) | TRANSCRICAO | [09:25] Diego |
| PRD-RNF-06 | docs/PRD.md | Requisito Não Funcional | Atomicidade: evento na transação do changeStatus | TRANSCRICAO | [09:41] Bruno |
| PRD-RNF-07 | docs/PRD.md | Requisito Não Funcional | Ordering por order_id com single-worker (limitação documentada) | TRANSCRICAO | [09:13] Larissa |
| PRD-RNF-08 | docs/PRD.md | Requisito Não Funcional | IDs em UUID (padrão do projeto) | TRANSCRICAO | [09:51] Larissa |
| PRD-RISCO-01 | docs/PRD.md | Risco | Churn: Atlas pode migrar se atrasar (Prob. Média / Imp. Alto) | TRANSCRICAO | [09:00] Marcos |
| PRD-RISCO-02 | docs/PRD.md | Risco | Cliente indisponível por janela longa (caso real de 2 h) | TRANSCRICAO | [09:16] Diego |
| PRD-RISCO-03 | docs/PRD.md | Risco | Acúmulo de eventos na outbox degrada o processamento | TRANSCRICAO | [09:08] Diego |
| PRD-RISCO-04 | docs/PRD.md | Risco | Vazamento de secret do lado do cliente (caso real) | TRANSCRICAO | [09:22] Diego |
| RFC-ALT-01 | docs/RFC.md | Alternativa descartada | Disparo síncrono no service de orders | TRANSCRICAO | [09:04] Bruno |
| RFC-ALT-02 | docs/RFC.md | Alternativa descartada | Redis Streams / fila externa (overengineering) | TRANSCRICAO | [09:07] Diego |
| RFC-ALT-03 | docs/RFC.md | Alternativa descartada | Trigger de banco para reatividade | TRANSCRICAO | [09:09] Diego |
| RFC-ALT-04 | docs/RFC.md | Alternativa descartada | Retry indefinido com backoff | TRANSCRICAO | [09:15] Diego |
| RFC-ALT-05 | docs/RFC.md | Alternativa descartada | 3 tentativas (agressivo demais) | TRANSCRICAO | [09:16] Bruno |
| RFC-ALT-06 | docs/RFC.md | Alternativa descartada | DLQ como flag `failed` na própria outbox | TRANSCRICAO | [09:18] Diego |
| RFC-ALT-07 | docs/RFC.md | Alternativa descartada | Secret global da plataforma | TRANSCRICAO | [09:21] Sofia |
| RFC-ALT-08 | docs/RFC.md | Alternativa descartada | Exactly-once (coordenação dos dois lados) | TRANSCRICAO | [09:25] Diego |
| RFC-OQ-01 | docs/RFC.md | Questão em aberto | Rate limiting de saída — observar e decidir depois | TRANSCRICAO | [09:38] Diego |
| RFC-OQ-02 | docs/RFC.md | Questão em aberto | Política de arquivamento da outbox (ex.: 30 dias) | TRANSCRICAO | [09:08] Diego |
| RFC-OQ-03 | docs/RFC.md | Questão em aberto | Escala horizontal / ordering global (futuro) | TRANSCRICAO | [09:13] Diego |
| RFC-OQ-04 | docs/RFC.md | Questão em aberto | Email de notificação de falhas (próxima fase) | TRANSCRICAO | [09:37] Larissa |
| RFC-RISCO-01 | docs/RFC.md | Risco | Prazo de fim de trimestre (pressão da Atlas) | TRANSCRICAO | [09:45] Marcos |
| RFC-RISCO-02 | docs/RFC.md | Risco | Indisponibilidade longa do cliente → DLQ | TRANSCRICAO | [09:17] Marcos |
| RFC-RISCO-03 | docs/RFC.md | Risco | Crescimento da outbox (arquivamento em aberto) | TRANSCRICAO | [09:08] Diego |
| RFC-RISCO-04 | docs/RFC.md | Restrição | Revisão de segurança obrigatória antes do deploy | TRANSCRICAO | [09:46] Sofia |
| FDD-FLUXO-01 | docs/FDD.md | Fluxo | Enfileiramento transacional no changeStatus (publishWebhookEvent(tx, ...)) | TRANSCRICAO | [09:41] Bruno |
| FDD-FLUXO-02 | docs/FDD.md | Fluxo | Worker lê pendentes por polling de 2 s em batch pequeno | TRANSCRICAO | [09:09] Diego |
| FDD-FLUXO-03 | docs/FDD.md | Fluxo | Retry com backoff 1 m/5 m/30 m/2 h/12 h (5 tentativas) | TRANSCRICAO | [09:17] Diego |
| FDD-FLUXO-04 | docs/FDD.md | Fluxo | Falha permanente move o evento para a DLQ; replay recoloca como PENDING | TRANSCRICAO | [09:18] Diego |
| FDD-EVENTO-01 | docs/FDD.md | Contrato | Payload JSON do evento (event_id, event_type, from/to_status, total_cents; sem items) | TRANSCRICAO | [09:43] Diego |
| FDD-EVENTO-02 | docs/FDD.md | Contrato | Headers de entrega (X-Event-Id, X-Signature, X-Timestamp, X-Webhook-Id, Content-Type) | TRANSCRICAO | [09:44] Diego |
| FDD-CONTRATO-01 | docs/FDD.md | Contrato | POST /api/v1/webhooks — cadastro (201; secret na resposta) | TRANSCRICAO | [09:31] Marcos |
| FDD-CONTRATO-02 | docs/FDD.md | Contrato | GET /api/v1/webhooks?customerId — listagem (200; sem secret) | TRANSCRICAO | [09:33] Bruno |
| FDD-CONTRATO-03 | docs/FDD.md | Contrato | PATCH /api/v1/webhooks/:id — edição | TRANSCRICAO | [09:33] Bruno |
| FDD-CONTRATO-04 | docs/FDD.md | Contrato | DELETE /api/v1/webhooks/:id — remoção (204) | TRANSCRICAO | [09:33] Bruno |
| FDD-CONTRATO-05 | docs/FDD.md | Contrato | POST /api/v1/webhooks/:id/secret/rotate — rotação (grace 24 h) | TRANSCRICAO | [09:21] Sofia |
| FDD-CONTRATO-06 | docs/FDD.md | Contrato | GET /api/v1/webhooks/:id/deliveries — últimos 100 entregas | TRANSCRICAO | [09:34] Marcos |
| FDD-CONTRATO-07 | docs/FDD.md | Contrato | POST /api/v1/admin/webhooks/dead-letter/:id/replay — replay (ADMIN) | TRANSCRICAO | [09:35] Diego |
| FDD-ERRO-01 | docs/FDD.md | Erro | WEBHOOK_NOT_FOUND (404) | TRANSCRICAO | [09:28] Bruno |
| FDD-ERRO-02 | docs/FDD.md | Erro | WEBHOOK_INVALID_URL (400) | TRANSCRICAO | [09:28] Bruno |
| FDD-ERRO-03 | docs/FDD.md | Erro | WEBHOOK_EVENT_FILTER_INVALID (400) — derivado do filtro de eventos por status | TRANSCRICAO | [09:33] Bruno |
| FDD-ERRO-04 | docs/FDD.md | Erro | WEBHOOK_SECRET_REQUIRED (422) | TRANSCRICAO | [09:28] Bruno |
| FDD-ERRO-05 | docs/FDD.md | Erro | WEBHOOK_PAYLOAD_TOO_LARGE (422) — acima de 64 KB | TRANSCRICAO | [09:24] Larissa |
| FDD-ERRO-06 | docs/FDD.md | Erro | WEBHOOK_DELIVERY_TIMEOUT — cliente não respondeu em 10 s | TRANSCRICAO | [09:42] Diego |
| FDD-ERRO-07 | docs/FDD.md | Erro | WEBHOOK_DELIVERY_FAILED — resposta fora de 2xx (retriável) | TRANSCRICAO | [09:42] Diego |
| FDD-ERRO-08 | docs/FDD.md | Erro | WEBHOOK_MAX_ATTEMPTS_EXCEEDED — 5 tentativas esgotadas → DLQ | TRANSCRICAO | [09:15] Diego |
| FDD-RES-01 | docs/FDD.md | Restrição | Atomicidade: enqueue dentro da transação; rollback remove o evento | TRANSCRICAO | [09:41] Bruno |
| FDD-RES-02 | docs/FDD.md | Restrição | Timeout de 10 s por tentativa de entrega | TRANSCRICAO | [09:42] Diego |
| FDD-RES-03 | docs/FDD.md | Decisão | Retry 5x com backoff exponencial | TRANSCRICAO | [09:17] Diego |
| FDD-RES-04 | docs/FDD.md | Decisão | DLQ em tabela separada com payload e motivo | TRANSCRICAO | [09:18] Diego |
| FDD-RES-05 | docs/FDD.md | Decisão | Replay exige role ADMIN e é auditado | TRANSCRICAO | [09:36] Larissa |
| FDD-RES-06 | docs/FDD.md | Decisão | At-least-once; dedup no cliente por X-Event-Id | TRANSCRICAO | [09:25] Diego |
| FDD-RES-07 | docs/FDD.md | Decisão | Snapshot do payload na inserção (evento imutável) | TRANSCRICAO | [09:52] Larissa |
| FDD-RES-08 | docs/FDD.md | Restrição | Payload máximo de 64 KB | TRANSCRICAO | [09:24] Diego |
| FDD-RES-09 | docs/FDD.md | Restrição | TLS obrigatório (somente https) | TRANSCRICAO | [09:23] Sofia |
| FDD-OBS-01 | docs/FDD.md | Proposta | Métricas do pipeline (entregas, pendentes, DLQ, latência) — operação da outbox | TRANSCRICAO | [09:08] Diego |
| FDD-OBS-02 | docs/FDD.md | Proposta | Logs estruturados com Pino (redaction existente) | TRANSCRICAO | [09:29] Bruno |
| FDD-OBS-03 | docs/FDD.md | Proposta | Correlação ponta a ponta pelo event_id / X-Event-Id | TRANSCRICAO | [09:44] Diego |
| FDD-CA-01 | docs/FDD.md | Critério de aceite | Evento gravado na mesma transação; rollback sem evento órfão | TRANSCRICAO | [09:06] Diego |
| FDD-CA-02 | docs/FDD.md | Critério de aceite | Filtro na inserção: sem webhook interessado ⇒ sem linha na outbox | TRANSCRICAO | [09:34] Bruno |
| FDD-CA-03 | docs/FDD.md | Critério de aceite | Entrega abaixo de 10 s no cenário local | TRANSCRICAO | [09:10] Larissa |
| FDD-CA-04 | docs/FDD.md | Critério de aceite | Retry na progressão 1 m/5 m/30 m/2 h/12 h | TRANSCRICAO | [09:17] Diego |
| FDD-CA-05 | docs/FDD.md | Critério de aceite | 5ª falha ⇒ DLQ com payload e motivo; replay recoloca | TRANSCRICAO | [09:18] Diego |
| FDD-CA-06 | docs/FDD.md | Critério de aceite | Assinatura HMAC-SHA256 verificável sobre o corpo | TRANSCRICAO | [09:20] Sofia |
| FDD-CA-07 | docs/FDD.md | Critério de aceite | URL http recusada; payload > 64 KB recusado | TRANSCRICAO | [09:23] Sofia |
| FDD-CA-08 | docs/FDD.md | Critério de aceite | Rotação: secret antiga válida por 24 h | TRANSCRICAO | [09:21] Sofia |
| FDD-CA-09 | docs/FDD.md | Critério de aceite | Replay exige ADMIN e registra auditoria | TRANSCRICAO | [09:36] Sofia |
| FDD-CA-10 | docs/FDD.md | Critério de aceite | Ordering por order_id com worker único | TRANSCRICAO | [09:12] Diego |
| FDD-INTEG-01 | docs/FDD.md | Integração | changeStatus chama publishWebhookEvent(tx, order, from, to) na mesma transação | CODIGO | src/modules/orders/order.service.ts |
| FDD-INTEG-02 | docs/FDD.md | Integração | Máquina de estados governa transições válidas e status notificáveis | CODIGO | src/modules/orders/order.status.ts |
| FDD-INTEG-03 | docs/FDD.md | Integração | Novas classes WEBHOOK_* seguem o padrão AppError/ErrorDetails | CODIGO | src/shared/errors/app-error.ts |
| FDD-INTEG-04 | docs/FDD.md | Integração | Error middleware central trata AppError/Zod/Prisma sem mudanças | CODIGO | src/middlewares/error.middleware.ts |
| FDD-INTEG-05 | docs/FDD.md | Integração | authenticate + requireRole('ADMIN') reaproveitados nas rotas | CODIGO | src/middlewares/auth.middleware.ts |
| FDD-INTEG-06 | docs/FDD.md | Integração | Módulo registrado em buildApiRouter (composição manual) | CODIGO | src/routes/index.ts |
| FDD-INTEG-07 | docs/FDD.md | Integração | src/worker.ts replica o padrão de bootstrap/shutdown do server | CODIGO | src/server.ts |
| FDD-INTEG-08 | docs/FDD.md | Integração | Novos modelos com UUID @db.Char(36) e @@map snake_case | CODIGO | prisma/schema.prisma |
| FDD-INTEG-09 | docs/FDD.md | Integração | Worker com instância própria de PrismaClient (client por processo) | CODIGO | src/config/database.ts |
| FDD-INTEG-10 | docs/FDD.md | Integração | Logger Pino com redaction reutilizado pelo worker | CODIGO | src/shared/logger/index.ts |
| ADR-001 | docs/adrs/ADR-001-outbox-no-mysql.md | Decisão | Padrão outbox no MySQL: evento na mesma transação da mudança de status | TRANSCRICAO | [09:08] Larissa |
| ADR-002 | docs/adrs/ADR-002-retry-backoff-e-dlq.md | Decisão | Retry 5x com backoff 1 m/5 m/30 m/2 h/12 h e DLQ em tabela separada | TRANSCRICAO | [09:17] Larissa |
| ADR-003 | docs/adrs/ADR-003-hmac-sha256-secret-por-endpoint.md | Decisão | HMAC-SHA256 sobre o corpo; secret por endpoint; rotação com grace de 24 h | TRANSCRICAO | [09:22] Sofia |
| ADR-004 | docs/adrs/ADR-004-at-least-once-x-event-id.md | Decisão | At-least-once com X-Event-Id (UUID) para dedup no cliente | TRANSCRICAO | [09:26] Larissa |
| ADR-005 | docs/adrs/ADR-005-worker-processo-separado-polling.md | Decisão | Worker em processo separado (src/worker.ts; npm run worker) com polling de 2 s | TRANSCRICAO | [09:11] Larissa |
| ADR-006 | docs/adrs/ADR-006-reuso-dos-padroes-existentes.md | Decisão | Reuso máximo dos padrões do projeto (módulo, erros WEBHOOK_*, Pino, middlewares) | TRANSCRICAO | [09:30] Larissa |
| ADR-007 | docs/adrs/ADR-007-uuid-e-snapshot-do-payload.md | Decisão | UUIDs (padrão do projeto) e snapshot do payload na inserção | TRANSCRICAO | [09:51] Larissa |

## Notas de cobertura

- **Total:** 108 itens mapeados — 98 com fonte `TRANSCRICAO` (90,7%) e 10 com fonte `CODIGO` (9,3%).
- **Critérios do desafio:** ≥ 80% de cobertura dos itens (atendido: 100% dos itens numerados dos
  documentos têm linha); ≥ 70% das linhas com `TRANSCRICAO` + timestamp válido (atendido: 90,7%);
  ≥ 5 linhas `CODIGO` com caminho real (atendido: 10 — caminhos conferidos com `git ls-files`).
- Todas as linhas `CODIGO` referem-se a arquivos **existentes** no repositório; o módulo
  `src/modules/webhooks` é o módulo **novo** a criar (aparece no FDD como proposta, não como
  arquivo existente).
