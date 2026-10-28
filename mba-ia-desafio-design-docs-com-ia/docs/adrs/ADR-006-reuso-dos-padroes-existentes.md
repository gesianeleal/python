# ADR-006: Reuso máximo dos padrões e componentes existentes do projeto

- **Status:** Aceito
- **Data:** 2026-10-28
- **Decisores:** Bruno (Engenharia de Pedidos), Diego (Engenharia de Plataforma), Larissa (Tech Lead)
- **Fonte primária:** `TRANSCRICAO.md` — [09:27]–[09:30]

## Contexto

O projeto já possui convenções consolidadas em toda a codebase: cada domínio é um módulo em
`src/modules` com `controller`, `service`, `repository`, `routes` e `schemas`; erros seguem o
padrão de uma classe base `AppError` com códigos específicos (`INSUFFICIENT_STOCK`,
`INVALID_STATUS_TRANSITION`); existe um middleware de erro centralizado que já trata `AppError`,
Zod e Prisma; o logger é Pino; validações usam Zod. A feature de webhooks é o primeiro módulo novo
desde essa consolidação, e a decisão sobre seguir (ou não) esses padrões afeta diretamente o custo
de manutenção e a consistência do sistema.

## Decisão

**Reuso máximo do que já existe** — o módulo de webhooks é "um módulo igual aos outros" ([09:30] Larissa):

1. **Estrutura**: criar `src/modules/webhooks` seguindo o padrão do projeto
   (controller / service / repository / routes / schemas), comparável aos módulos existentes como
   `src/modules/orders` ([09:27] Bruno).
2. **Erros**: códigos com prefixo **`WEBHOOK_`** (`WEBHOOK_NOT_FOUND`, `WEBHOOK_INVALID_URL`,
   `WEBHOOK_SECRET_REQUIRED`, ...), reaproveitando as classes existentes de
   `src/shared/errors/app-error.ts` e `src/shared/errors/http-errors.ts` (mesmo padrão de
   `InvalidStatusTransitionError` e `InsufficientStockError`) ([09:28] Bruno; [09:29] Larissa).
3. **Middleware de erro**: nenhuma mudança — `src/middlewares/error.middleware.ts` já trata
   `AppError`, Zod e Prisma e "vai pegar nossos erros sem precisar mudar nada" ([09:29] Bruno).
4. **Logger**: manter Pino (`src/shared/logger/index.ts`), sem biblioteca nova ([09:29] Bruno).
5. **Auth**: reutilizar `authenticate` e `requireRole` de `src/middlewares/auth.middleware.ts`
   (usado no replay de DLQ; ver ADR-002) ([09:36] Larissa).
6. **Prisma**: worker com instância **própria** do PrismaClient do processo (mesmo banco, mesma
   `DATABASE_URL`) — o client é por processo Node ([09:29]–[09:30] Bruno/Diego).
7. **Worker**: lógica de processamento dentro do módulo (`webhook.worker.ts` / `webhook.processor.ts`),
   com entry point `src/worker.ts` ([09:28] Bruno).

## Alternativas consideradas

1. **Criar uma stack paralela para o módulo** (bibliotecas/abstrações novas de erro, logger ou
   validação) — descartada como diretriz em [09:29]–[09:30]:
   nada novo entra; o valor está em consistência e menor custo de manutenção para todo o time.
2. **Compartilhar a instância do PrismaClient entre API e worker** — descartada em [09:29]–[09:30]:
   o PrismaClient é por processo; o worker é outro processo Node e usa uma instância nova sobre o
   mesmo banco.

## Consequências

**Positivas:**
- Consistência com a codebase: o módulo novo é reconhecível e navegável por qualquer dev do time.
- Tratamento de erros pronto: o middleware central já responde erros `WEBHOOK_*` sem mudanças ([09:29]).
- Menor superfície de revisão de segurança (Sofia) e menor custo de aprendizado.

**Negativas / trade-offs:**
- O módulo herda limitações dos padrões atuais (ex.: composição manual de dependências em
  `src/app.ts`/`src/routes/index.ts`) — aceito como custo da consistência.
- Sem libs novas também significa resolver na mão o que uma lib faria (ex.: backoff do retry) —
  aceito; a política (ADR-002) é simples o bastante.
