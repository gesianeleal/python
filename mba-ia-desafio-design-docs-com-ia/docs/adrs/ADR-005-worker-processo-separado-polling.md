# ADR-005: Worker em processo separado com polling de 2 segundos

- **Status:** Aceito
- **Data:** 2026-10-28
- **Decisores:** Diego (Engenharia de Plataforma), Larissa (Tech Lead), Bruno (Engenharia de Pedidos)
- **Fonte primária:** `TRANSCRICAO.md` — [09:08]–[09:13]

## Contexto

Definido o padrão outbox (ADR-001), é preciso decidir **como** o processador lê a tabela e
**onde** ele roda. O requisito de negócio é entrega abaixo de 10 segundos ([09:02]), e o ciclo de
vida do processador não pode ficar refém da API: se o processo da API reinicia, o processamento de
eventos não pode parar junto ([09:11] Diego).

Restrição técnica relevante: o MySQL **não tem listener nativo** (não existe algo como
`NOTIFY/LISTEN` do PostgreSQL), então reatividade via banco não é viável sem improvisos ([09:09]).

## Decisão

1. **Worker em processo separado**: nova entry point `src/worker.ts` com script `npm run worker`,
   nos mesmos moldes do `src/server.ts` existente ([09:11] Larissa).
2. **Polling em loop a cada 2 segundos**: busca os eventos pendentes mais antigos, processa,
   marca como entregue ([09:09] Diego). O pior caso de latência inicial é 2 segundos, o que
   atende "abaixo de 10 segundos" com folga ([09:09]–[09:10]).
3. O worker conecta **no mesmo banco** e usa a **mesma stack (Prisma)**, mas com **instância
   própria do PrismaClient** — o client é por processo Node ([09:11], [09:29]–[09:30]).
4. **Single-worker nesta fase**, com ordering implícita por `order_id` (eventos do mesmo pedido
   são processados na ordem de `created_at` da outbox). **Não há garantia de ordering global** —
   limitação conhecida e documentada ([09:12]–[09:13]).

## Alternativas consideradas

1. **Trigger de banco para reatividade** — descartada em [09:09]:
   o MySQL não notifica processo externo; a trigger só executa SQL. Improvisar (escrever em
   arquivo, bater em endpoint) "fica esquisito" e não se justifica — polling de 2 s atende o requisito.
2. **Worker embutido no processo da API** — descartada em [09:11]:
   se a API reinicia, perde-se o worker junto; o processamento precisa de ciclo de vida próprio.
3. **Múltiplos workers em paralelo (escala horizontal)** — adiada em [09:13]:
   perderia a ordering por `order_id`; particionamento por `order_id` ou lock pessimista ficam
   como "problema do futuro", não desta fase.

## Consequências

**Positivas:**
- Latência de entrega bem abaixo do requisito de 10 s (pior caso inicial de ~2 s + tempo de resposta) ([09:10]).
- O ciclo de vida do worker é independente da API; reinícios não perdem processamento ([09:11]).
- Reuso integral do stack (mesmo banco, mesmo Prisma, mesma stack) ([09:11]).

**Negativas / trade-offs:**
- Latência mínima artificial de até 2 s por design (aceita explicitamente em [09:10]).
- **Sem ordering global** e sem escala horizontal nesta fase; ordering vale por `order_id` e
  apenas enquanto houver um único worker ([09:12]–[09:13]).
- Um serviço adicional a implantar e operar (novo processo/deployment).
