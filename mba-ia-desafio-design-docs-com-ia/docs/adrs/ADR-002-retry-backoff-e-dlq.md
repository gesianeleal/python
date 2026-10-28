# ADR-002: Retry com backoff exponencial e DLQ persistida em tabela separada

- **Status:** Aceito
- **Data:** 2026-10-28
- **Decisores:** Diego (Engenharia de Plataforma), Bruno (Engenharia de Pedidos), Larissa (Tech Lead), Marcos (Product Manager)
- **Fonte primária:** `TRANSCRICAO.md` — [09:14]–[09:19], [09:35]–[09:36]

## Contexto

O worker entrega eventos via HTTP para endpoints de clientes, que podem estar temporariamente
indisponíveis: já houve cliente com indisponibilidade de duas horas em manutenção planejada
([09:16] Diego). É preciso uma política que (a) absorva janelas realistas de indisponibilidade,
(b) não deixe eventos "pendurados para sempre", e (c) preserve evidência e permita
reprocessamento quando a entrega falhar definitivamente.

## Decisão

1. **5 tentativas** por evento, com **backoff exponencial**: 1 minuto, 5 minutos, 30 minutos,
   2 horas e 12 horas após a primeira falha — total de quase 15 horas entre a primeira falha e a
   última tentativa ([09:15]–[09:17]).
2. Esgotadas as tentativas, o evento é considerado falha permanente e movido para uma **tabela
   separada `webhook_dead_letter`**, com payload, motivo da falha e timestamp ([09:18]).
3. **Reprocessamento manual** via endpoint administrativo
   `POST /admin/webhooks/dead-letter/:id/replay`, que recoloca o evento na outbox como pendente
   ([09:18]).
4. O acesso ao replay exige **role `ADMIN`** e a ação deve ser **auditada** (registro de quem
   executou) ([09:35]–[09:36] Sofia).

## Alternativas consideradas

1. **Retry indefinido com backoff** — descartada em [09:15]:
   traria o problema de evento pendurado para sempre se o cliente simplesmente sumir; a janela
   de 15 horas é o teto negociado com o negócio.
2. **3 tentativas** — descartada em [09:16]:
   agressivo demais; cobriria apenas ~30 minutos e mataria entregas para clientes com
   indisponibilidade de manhã ([09:16] Diego: "3 é pouco").
3. **DLQ como marcação `failed` na própria tabela de outbox** — descartada em [09:18]:
   poluiria a leitura da outbox principal; a tabela separada mantém a leitura limpa e serve como
   evidência de debug e reprocessamento.

## Consequências

**Positivas:**
- Cobre indisponibilidades reais de até ~15 horas antes de desistir ([09:17]).
- A DLQ separada preserva payload e motivo da falha como evidência para debug e auditoria ([09:18]).
- O replay manual dá controle operacional sem exigir reprocessamento automático complexo.

**Negativas / trade-offs:**
- Falha definitiva após ~15 horas ainda depende de intervenção humana (replay) — aceito ([09:17]).
- Adiciona uma tabela e um endpoint administrativo ao escopo ([09:18]).
- Eventos em DLQ ficam "invisíveis" para o cliente até um replay — não há notificação ativa
  nesta fase (ver "Fora de escopo" do PRD: email fica para a próxima fase, [09:37]–[09:38]).
