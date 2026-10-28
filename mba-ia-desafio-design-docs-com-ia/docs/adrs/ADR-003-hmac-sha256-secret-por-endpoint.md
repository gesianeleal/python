# ADR-003: Autenticação HMAC-SHA256 com secret por endpoint e rotação com grace period

- **Status:** Aceito
- **Data:** 2026-10-28
- **Decisores:** Sofia (Engenharia de Segurança), Diego (Engenharia de Plataforma), Bruno (Engenharia de Pedidos), Larissa (Tech Lead)
- **Fonte primária:** `TRANSCRICAO.md` — [09:19]–[09:22]

## Contexto

Os eventos expõem dados de pedidos para endpoints **fora da infraestrutura da empresa**. O cliente
precisa conseguir validar que a requisição veio realmente da plataforma e que o payload não foi
adulterado no caminho ([09:19] Sofia). O risco é concreto: já houve caso de cliente que vazou
secret em log da própria aplicação ([09:22] Diego), e uma secret global de plataforma significaria
que "se vaza uma, vaza tudo" ([09:21] Sofia).

Além disso, secrets precisam ser rotacionáveis sem quebrar a integração do cliente: a troca
precisa ser negociável no tempo, não um corte seco.

## Decisão

1. Assinar o **corpo do request** com **HMAC-SHA256** (padrão de mercado; "todo cliente sério tem
   biblioteca para isso" — [09:20] Sofia) e enviar a assinatura no header `X-Signature` ([09:20]).
2. **Secret única por endpoint de webhook** — não uma secret global da plataforma. A configuração
   do webhook armazena `url + secret + customer_id + estado ativo` ([09:21]).
3. A secret é **gerada pela plataforma e devolvida na criação** do webhook ([09:31] Marcos).
4. **Rotação self-service** via endpoint do cliente, com a secret antiga permanecendo válida por
   **24 horas em paralelo** (grace period) para o cliente migrar seus sistemas; depois disso, a
   antiga morre ([09:21] Sofia).
5. Complemento de segurança: **TLS obrigatório** — URL de webhook deve ser `https`; cadastro com
   `http` é recusado como erro de validação ([09:23] Sofia).

## Alternativas consideradas

1. **Secret global da plataforma** — descartada em [09:21]:
   um vazamento comprometeria todos os clientes ("se vaza uma, vaza tudo"); o isolamento por
   endpoint limita o comprometimento a um cliente.
2. **Confiar apenas em HTTPS sem assinatura** — não considerada suficiente ([09:19]–[09:20]):
   TLS protege o transporte, mas não permite ao cliente validar a origem da chamada nem detectar
   adulteração do payload no ponto de chegada; a assinatura é a verificação que o cliente controla.

## Consequências

**Positivas:**
- Comprometimento de uma secret fica limitado a um único endpoint de um único cliente ([09:21]).
- Rotação sem downtime de integração, com convivência de 24 horas entre secrets ([09:21]).
- Verificação do lado do cliente é barata e padrão de mercado ([09:20]).

**Negativas / trade-offs:**
- Mais complexidade de modelo e de operação: dois secrets por endpoint durante o grace period e
  um endpoint dedicado de rotação ([09:21]).
- Transfere parte do esforço de segurança para o cliente (implementar a verificação HMAC) —
  mitigado pela documentação no portal do desenvolvedor ([09:26] Marcos).
- Secrets em texto utilizável exigem cuidado de armazenamento e nunca podem aparecer em logs;
  o logger Pino do projeto já possui redaction configurada para tokens ([09:29]).
