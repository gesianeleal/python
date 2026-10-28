# ADR-004: Garantia at-least-once com deduplicação por X-Event-Id

- **Status:** Aceito
- **Data:** 2026-10-28
- **Decisores:** Diego (Engenharia de Plataforma), Sofia (Engenharia de Segurança), Bruno (Engenharia de Pedidos), Larissa (Tech Lead)
- **Fonte primária:** `TRANSCRICAO.md` — [09:24]–[09:26]

## Contexto

O sistema precisa definir a garantia de entrega dos eventos. A entrega envolve dois sistemas
independentes (plataforma e cliente) e qualquer política mais forte exige coordenação entre as
partes. O worker pode reenviar um evento após uma falha ambígua (timeout sem resposta definitiva
do cliente), então a política precisa ser explícita sobre o que pode acontecer em duplicidade.

## Decisão

1. A plataforma garante **at-least-once**: pode acontecer de o cliente receber o mesmo evento
   duas vezes, e ele tem que estar preparado ([09:24] Diego).
2. Cada evento carrega um **`X-Event-Id`** (UUID, gerado quando o evento entra na outbox —
   ver ADR-007), único por evento; **a deduplicação é responsabilidade do cliente**, pelo
   `event_id` ([09:25]).
3. O comportamento é documentado em destaque no portal do desenvolvedor para os clientes
   ([09:26] Marcos).

## Alternativas consideradas

1. **Exactly-once** — descartada em [09:24]–[09:25]:
   exigiria coordenação dos dois lados da integração e ficaria "muito mais complexo";
   at-least-once com `event_id` resolve 99% dos casos, seguindo o padrão de mercado
   (Stripe e GitHub operam assim — [09:25] Diego).

## Consequências

**Positivas:**
- Simplicidade de implementação na plataforma: sem protocolo de confirmação transacional
  de dois lados ([09:25]).
- Padrão de mercado reconhecido: clientes sérios já estão familiarizados com deduplicação por
  `event_id` ([09:25]).

**Negativas / trade-offs:**
- Duplicatas são possíveis por design; quem não deduplicar pode processar o mesmo evento duas
  vezes ([09:24]).
- Transfere responsabilidade ao cliente (já identificado como ponto sensível por Sofia em
  [09:25]) — mitigado pela documentação destacada no portal ([09:26]).
