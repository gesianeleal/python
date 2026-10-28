# ADR-007: UUIDs e snapshot do payload na inserção do evento na outbox

- **Status:** Aceito
- **Data:** 2026-10-28
- **Decisores:** Larissa (Tech Lead), Diego (Engenharia de Plataforma), Bruno (Engenharia de Pedidos)
- **Fonte primária:** `TRANSCRICAO.md` — [09:51]–[09:52]

## Contexto

Ao modelar a tabela da outbox (ADR-001), duas decisões de detalhe surgiram no fim da reunião:
o tipo do identificador dos eventos e **quando** renderizar o payload JSON que será entregue ao
cliente. A segunda tem consequência semântica relevante: um pedido pode mudar de status várias
vezes depois; se o payload for renderizado apenas no momento do envio, o evento pode refletir um
estado diferente daquele que o originou ([09:51] Bruno).

O restante do projeto usa **UUID** como padrão de identificadores (todos os modelos do
`prisma/schema.prisma` usam `@id @default(uuid()) @db.Char(36)`) ([09:51] Larissa).

## Decisão

1. **Identificadores em UUID**: tanto o id da linha da outbox quanto o `event_id` (usado no
   header `X-Event-Id` — ADR-004) são UUIDs, seguindo o padrão do projeto ([09:51]).
2. **Snapshot do payload na inserção**: o payload renderizado é gravado **no momento em que o
   evento entra na outbox**, dentro da transação da mudança de status. O evento permanece imutável
   e reflete o estado do pedido quando o status mudou; mudanças posteriores do pedido não afetam
   o evento já registrado ([09:51]–[09:52] Larissa/Diego).

## Alternativas consideradas

1. **Id auto incremental** — descartada em [09:51]:
   "segue o padrão do resto do projeto. Tudo é uuid" ([09:51] Larissa); além disso, ids
   sequenciais expõem volume de eventos.
2. **Renderizar o payload na hora do envio** (guardar apenas `order_id` na outbox) — descartada
   em [09:51]–[09:52]:
   se o pedido mudar depois, o evento entregue refletiria um estado diferente do que motivou a
   notificação — "caso esquisito" explicitamente rejeitado ([09:52] Larissa).

## Consequências

**Positivas:**
- Consistência total com o padrão de identificação do projeto (UUID em todos os modelos) ([09:51]).
- Cada evento é um snapshot imutável e auditável do momento da transição — o cliente recebe
  exatamente o estado que gerou a notificação ([09:52]).
- Rendering pesado fica fora do caminho crítico de envio (o worker apenas lê o payload pronto).

**Negativas / trade-offs:**
- Duplicação de dados: payload completo armazenado por evento na outbox (custo de storage aceito).
- Evoluções de schema do payload não "retrofitam" eventos antigos — o snapshot é o contrato
  daquele momento; qualquer mudança de formato passa a valer para eventos novos.
