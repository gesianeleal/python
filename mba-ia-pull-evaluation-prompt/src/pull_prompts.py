"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml
"""

import sys

from dotenv import load_dotenv
from langsmith import Client

from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

SEED_PROMPT = "leonanluppi/bug_to_user_story_v1"
OUTPUT_PATH = "prompts/bug_to_user_story_v1.yml"


def pull_prompts_from_langsmith():
    """
    Faz o pull do prompt semente e devolve um dict no formato do YAML local.

    `dangerously_pull_public_prompt=True` é obrigatório: o LangSmith bloqueia
    por padrão o pull de prompts com dono explícito ("owner/nome"), porque um
    prompt do Hub é um objeto LangChain serializado, que pode vir de terceiros.
    Aqui o prompt é o semente do desafio — risco conhecido e aceito.
    """
    client = Client()
    prompt = client.pull_prompt(SEED_PROMPT, dangerously_pull_public_prompt=True)

    messages = getattr(prompt, "messages", [])
    system_prompt = messages[0].prompt.template if len(messages) > 0 else ""
    user_prompt = messages[1].prompt.template if len(messages) > 1 else "{bug_report}"

    return {
        "bug_to_user_story_v1": {
            "description": "Prompt para converter relatos de bugs em User Stories",
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "version": "v1",
            "tags": ["bug-analysis", "user-story", "product-management"],
        }
    }


def main():
    """Função principal"""
    print_section_header("PULL DO PROMPT SEMENTE (LangSmith Hub)")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    print(f"Fonte: {SEED_PROMPT}")

    try:
        prompt_data = pull_prompts_from_langsmith()
    except Exception as erro:
        print(f"❌ Falha no pull: {erro}")
        return 1

    if not save_yaml(prompt_data, OUTPUT_PATH):
        return 1

    print(f"✓ Prompt salvo em {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
