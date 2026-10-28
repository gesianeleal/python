# PRD — Sistema de Webhooks de Notificação de Pedidos

| Campo | Valor |
| ----- | ----- |
| **Autor** | Gesiane Leal |
| **Data** | 2026-10-28 |
| **Status** | Em revisão |
| **Documentos relacionados** | `docs/RFC.md`, `docs/FDD.md`, `docs/adrs/` |

## 1. Resumo e contexto

A plataforma opera um Order Management System (OMS) em produção com módulos de autenticação,
usuários, clientes, produtos e pedidos (máquina de estados controlada, controle transacional de
estoque e auditoria de mudanças de status). **Não existe hoje nenhum mecanismo de notificação
externa** — nem eventos, nem filas, nem webhooks.

Esta feature entrega um **sistema de webhooks de notificação de pedidos** (outbound): os clientes
cadastram endpoints e passam a receber, em tempo real (abaixo de 10 segundos), os eventos de
mudança de status dos seus pedidos, com entrega assinada, retry automático e histórico de entregas
consultável ([09:00]–[09:02], [09:31]–[09:36]).

## 2. Problema e motivação

- Três clientes B2B — **Atlas Comercial, MaxDistribuição e Nova Cargo** — pediram formalmente
  notificação em tempo real das mudanças de status dos seus pedidos ([09:00] Marcos).
- Hoje eles fazem **polling no `GET /orders`** repetidamente para descobrir mudanças, o que torna
  a integração **lenta e cara** para eles ([09:00]).
- A Atlas sinalizou **risco de migração para concorrente** se a entrega não acontecer até o fim do
  trimestre ([09:00]) — há pressão de negócio real sobre o prazo.
- "Tempo real", para esses clientes, significa **qualquer latência abaixo de 10 segundos**
  ([09:02] Marcos) — o importante é não ficar pendurado exigindo atualização manual.

## 3. Público-alvo e cenários de uso

**Público-alvo primário:** times de integração dos clientes B2B (Atlas Comercial, MaxDistribuição,
Nova Cargo) que consomem a API da plataforma.

**Público-alvo secundário:** operadores internos com role `ADMIN` que acompanham a operação das
entregas e executam replays manuais de DLQ ([09:35]–[09:36]).

**Cenário principal:** um pedido do cliente muda de status (ex.: `PAID` → `PROCESSING`); o cliente
recebe um POST assinado no endpoint cadastrado em menos de 10 segundos, valida a assinatura,
processa o evento (deduplicando por `X-Event-Id`) e atualiza seus sistemas internos.

**Cenários secundários:**
- Cliente cadastra um webhook escolhendo os status de interesse (ex.: "só quero ouvir `SHIPPED`
  e `DELIVERED`") ([09:33] Marcos).
- Cliente consulta o histórico das últimas entregas (sucesso/falha, payload, resposta, tempo de
  resposta) para diagnosticar sua integração ([09:34] Marcos).
- Cliente rotaciona a secret do endpoint com migração sem downtime (grace period de 24 h) ([09:21] Sofia).
- Operador `ADMIN` reprocessa um evento que caiu em DLQ após esgotar as tentativas ([09:18], [09:36]).

## 4. Objetivos e métricas de sucesso

| ID | Objetivo | Métrica | Meta |
| -- | -------- | ------- | ---- |
| PRD-MET-01 | Notificar mudanças de status em tempo real | Percentual de eventos entregues com latência abaixo de 10 s (p95) | **≥ 95%** ([09:02], [09:10]) |
| PRD-MET-02 | Não perder eventos de mudanças commitadas | Percentual de mudanças de status commitadas com evento correspondente na outbox | **100%** ([09:06], [09:41]) |
| PRD-MET-03 | Eliminar o polling manual dos clientes integrados | Clientes B2B da fase 1 integrados consumindo webhooks em vez de polling | **3 de 3** (Atlas, MaxDistribuição, Nova Cargo) ([09:00], [09:47]) |
| PRD-MET-04 | Absorver indisponibilidades dos clientes | Percentual de eventos entregues com até 5 tentativas (~15 h de janela) | ≥ 99% antes de DLQ ([09:15]–[09:17]) |

## 5. Escopo

### Incluso
- CRUD de configuração de webhooks por customer (criar, listar, editar, remover), com secret
  gerada na criação e lista de eventos de interesse ([09:31]–[09:33]).
- Rotação de secret self-service com grace period de 24 h ([09:21]).
- Motor de eventos: outbox transacional, worker de entrega com polling de 2 s, retry com backoff
  e DLQ com replay administrativo ([09:06]–[09:18]).
- Entrega assinada com HMAC-SHA256, headers de identificação e payload enxuto do evento
  ([09:20]–[09:25], [09:43]–[09:44]).
- Histórico de entregas consultável pelo cliente (últimos 100) ([09:34]).
- Documentação de integração para os clientes no portal do desenvolvedor ([09:26], [09:36]).

### Fora de escopo (descartado ou adiado na reunião)
| ID | Item | Situação |
| -- | ---- | -------- |
| PRD-OUT-01 | **Email de aviso** ao cliente quando o webhook dele falha repetidamente | Adiado para próxima fase, depois de medir o impacto ([09:37]–[09:38]) |
| PRD-OUT-02 | **Rate limiting de saída** (limitar volume de chamadas por cliente) | Adiado: "observar e decidir depois" — registrado como questão em aberto ([09:38]–[09:39]) |
| PRD-OUT-03 | **Dashboard visual** para o cliente acompanhar webhooks | Descartado: painel é projeto separado do time de frontend ([09:39]–[09:40]) |
| PRD-OUT-04 | **Arquivamento de linhas entregues da outbox** | Fora do escopo desta feature; política (ex.: 30 dias) a definir ([09:08]) |
| PRD-OUT-05 | **Webhooks inbound** (cliente → plataforma) | Descartado no início: "só saindo da gente pra eles" ([09:02]) |
| PRD-OUT-06 | **Ordering global / múltiplos workers** | Fora do escopo da fase: ordering por `order_id` com single-worker; escala fica para o futuro ([09:12]–[09:13]) |

## 6. Requisitos funcionais

| ID | Requisito | Fonte |
| -- | --------- | ----- |
| PRD-FR-01 | O cliente pode **cadastrar** um webhook por customer (`POST`), informando url e a lista de status que deseja receber; a **secret é gerada pela plataforma e devolvida na criação**; o `customer_id` é informado no body da requisição (não vem do JWT) | [09:31]–[09:32] |
| PRD-FR-02 | O cliente pode **listar** os webhooks de um customer (`GET`) | [09:33] |
| PRD-FR-03 | O cliente pode **editar** um webhook (`PATCH`) | [09:33] |
| PRD-FR-04 | O cliente pode **remover** um webhook (`DELETE`) | [09:33] |
| PRD-FR-05 | Os eventos são **filtrados pelos status de interesse na inserção** na outbox: se nenhum webhook do customer quer aquele status, o evento nem é registrado | [09:33]–[09:34] |
| PRD-FR-06 | O cliente pode consultar o **histórico de entregas** de um webhook (`GET /webhooks/:id/deliveries`): últimos 100, com sucesso/falha, payload, resposta e tempo de resposta | [09:34] |
| PRD-FR-07 | Um operador `ADMIN` pode **reprocessar manualmente** um evento da DLQ (`POST /admin/webhooks/dead-letter/:id/replay`), recolocando-o na outbox como pendente; a ação é auditada (registro de quem executou) | [09:18], [09:35]–[09:36] |
| PRD-FR-08 | O cliente pode **rotacionar a secret** do endpoint via API; a secret antiga permanece válida por 24 h em paralelo (grace period) e depois deixa de valer | [09:21] |
| PRD-FR-09 | O cliente recebe **notificação outbound** (`order.status_changed`) quando o status de um pedido seu muda, em menos de 10 segundos | [09:00]–[09:02], [09:09]–[09:10] |
| PRD-FR-10 | Cada entrega é **assinada (HMAC-SHA256)** e identificada com `X-Event-Id`, `X-Webhook-Id`, `X-Timestamp` e `X-Signature`, permitindo ao cliente validar origem/integridade e deduplicar | [09:20]–[09:25], [09:44] |

## 7. Requisitos não funcionais

| ID | Requisito | Fonte |
| -- | --------- | ----- |
| PRD-RNF-01 | Latência de entrega abaixo de 10 s (o polling de 2 s do worker garante o pior caso inicial) | [09:02], [09:10] |
| PRD-RNF-02 | URLs de webhook devem ser **HTTPS**; cadastro com `http` é recusado como erro de validação | [09:23] |
| PRD-RNF-03 | Payload limitado a **64 KB**; acima disso a entrega é recusada com erro (sem truncamento) | [09:23]–[09:24] |
| PRD-RNF-04 | Timeout de **10 s** por chamada HTTP de entrega; cliente lento conta como falha e entra em retry | [09:42] |
| PRD-RNF-05 | Garantia de entrega **at-least-once**; o cliente deduplica pelo `X-Event-Id` (UUID por evento) | [09:24]–[09:25] |
| PRD-RNF-06 | Atomicidade: o evento é registrado na mesma transação SQL da mudança de status; rollback da transação remove o evento | [09:06], [09:40]–[09:41] |
| PRD-RNF-07 | Ordering: garantida apenas **por `order_id`** e com single-worker; sem garantia de ordering global (limitação documentada) | [09:12]–[09:13] |
| PRD-RNF-08 | Identificadores da feature seguem o padrão **UUID** do projeto; módulo reutiliza os padrões existentes (sem bibliotecas novas) | [09:27]–[09:30], [09:51] |

## 8. Decisões e trade-offs principais

| Decisão | Trade-off aceito | ADR |
| ------- | ---------------- | --- |
| Padrão outbox no MySQL (nada síncrono) | Latência mínima de ~2 s pelo polling; crescimento da tabela | [ADR-001](adrs/ADR-001-outbox-no-mysql.md) |
| Retry 5x com backoff (1 m/5 m/30 m/2 h/12 h) + DLQ separada | Falha definitiva após ~15 h exige replay manual | [ADR-002](adrs/ADR-002-retry-backoff-e-dlq.md) |
| HMAC-SHA256 com secret por endpoint e rotação 24 h | Mais complexidade de operação; cliente precisa implementar verificação | [ADR-003](adrs/ADR-003-hmac-sha256-secret-por-endpoint.md) |
| At-least-once com `X-Event-Id` | Duplicatas possíveis; deduplicação é responsabilidade do cliente | [ADR-004](adrs/ADR-004-at-least-once-x-event-id.md) |
| Worker separado com polling de 2 s | Sem ordering global; um serviço a mais para operar | [ADR-005](adrs/ADR-005-worker-processo-separado-polling.md) |
| Reuso máximo dos padrões do projeto | Herda limitações atuais; alguns itens resolvidos "na mão" | [ADR-006](adrs/ADR-006-reuso-dos-padroes-existentes.md) |
| UUIDs + snapshot do payload na inserção | Duplicação de dados na outbox; eventos antigos não ganham schema novo | [ADR-007](adrs/ADR-007-uuid-e-snapshot-do-payload.md) |

## 9. Dependências

- **Plataforma**: aplicação OMS existente (Node.js/TypeScript, Prisma/MySQL), API autenticada por
  JWT com roles `ADMIN`/`OPERATOR` ([09:32], [09:36]).
- **Infraestrutura**: MySQL existente; nenhuma infraestrutura nova ([09:07]).
- **Times**: revisão de segurança da Sofia (≥ 2 dias úteis antes do deploy) ([09:46]).
- **Clientes**: implementar no lado deles a verificação HMAC e a deduplicação por `X-Event-Id`
  ([09:25]–[09:26]).
- **Documentação**: portal do desenvolvedor com guia de integração (Marcos) ([09:26], [09:36], [09:40]).

## 10. Riscos e mitigação

| ID | Risco | Probabilidade | Impacto | Mitigação |
| -- | ----- | ------------- | ------- | --------- |
| PRD-RISCO-01 | **Churn de cliente por atraso**: a Atlas migrar para concorrente se a entrega não sair até o fim do trimestre | Média | Alto | Prazo assumido de 3 sprints com revisão de segurança incluída no fim; atualização proativa dos clientes pelo PM ([09:00], [09:45]–[09:47]) |
| PRD-RISCO-02 | **Cliente indisponível por janela longa**: eventos não entregues e percepção de "pendurado" | Média | Médio | Retry de até ~15 h; DLQ com evidência (payload/motivo) e replay manual via endpoint admin ([09:15]–[09:18]) |
| PRD-RISCO-03 | **Acúmulo na outbox** degrada o processamento com o tempo | Baixa | Médio | Índice em status/`created_at` e leitura em batch pequeno; alternativa de arquivamento registrada para fase futura ([09:08]) |
| PRD-RISCO-04 | **Vazamento de secret** do lado do cliente (já observado em cliente real) | Média | Alto | Secret única por endpoint (limita o alcance), rotação self-service com grace de 24 h e revisão de segurança dedicada antes do deploy ([09:21]–[09:22], [09:46]) |

## 11. Critérios de aceitação (produto)

1. Cliente cadastra um webhook (url + eventos) e recebe a secret uma única vez na criação ([09:31]–[09:32]).
2. Mudanças de status commitadas geram entrega assinada em < 10 s para todos os webhooks do
   customer interessados naquele status ([09:02], [09:09]–[09:10]).
3. Cadastro com URL `http` é recusado; payload acima de 64 KB é recusado ([09:23]–[09:24]).
4. Entregas com falha são retentadas na progressão definida; esgotadas as 5 tentativas, o evento
   fica na DLQ e pode ser reprocessado por um `ADMIN` com registro de auditoria ([09:15]–[09:18], [09:36]).
5. Cliente consulta as últimas 100 entregas com sucesso/falha, payload, resposta e tempo de
   resposta ([09:34]).
6. Rotação de secret funciona com a antiga válida por 24 h ([09:21]).
7. Nenhuma mudança de status commitada fica sem evento correspondente na outbox ([09:06], [09:41]).

## 12. Estratégia de testes e validação

- **Testes de integração (Vitest)** no padrão do projeto (`tests/orders.test.ts`,
  `tests/helpers/factories.ts`): CRUD de webhooks, validações (https, eventos válidos), rotação
  de secret, autorização `ADMIN` no replay.
- **Testes de transação**: rollback da mudança de status não pode deixar evento na outbox;
  commit grava evento com snapshot correto.
- **Testes do worker**: processamento em batch, retry com backoff (tempos reduzidos via
  configuração de teste), timeout, movimentação para DLQ e replay.
- **Entrega de ponta a ponta**: cliente simulado (servidor HTTP local) verificando assinatura
  HMAC, deduplicação por `X-Event-Id` e medição de latência.
- **Validação de segurança**: revisão dedicada da Sofia (HMAC e geração/rotação de secret) antes
  do deploy ([09:46]).
