from search import search_prompt


def main():
    chain = search_prompt()

    if not chain:
        print("Não foi possível iniciar o chat. Verifique os erros de inicialização.")
        return

    print("Chat com o PDF — pergunte algo (digite 'sair' para encerrar).")

    while True:
        try:
            pergunta = input("\nPERGUNTA: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not pergunta:
            continue
        if pergunta.lower() in {"sair", "exit", "quit"}:
            break

        try:
            resposta = chain.invoke(pergunta)
        except Exception as erro:
            print(f"\nErro ao consultar: {erro}")
            continue

        print(f"\nRESPOSTA: {resposta}")

    print("Até logo!")


if __name__ == "__main__":
    main()
