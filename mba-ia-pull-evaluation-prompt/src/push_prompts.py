"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)
"""

import os
import sys

from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate

from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPT_FILE = "prompts/bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    client = Client()

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_data["system_prompt"]),
            ("user", prompt_data["user_prompt"]),
        ]
    )

    description = prompt_data.get("description", "Prompt otimizado do desafio")
    techniques = prompt_data.get("techniques_applied", [])
    if techniques:
        description = f"{description} Técnicas aplicadas: {', '.join(techniques)}."

    url = client.push_prompt(
        prompt_name,
        object=prompt,
        is_public=True,
        description=description,
        tags=prompt_data.get("tags", []),
    )

    print(f"✓ Prompt publicado (público): {url}")
    return True


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    for field in ("description", "system_prompt", "user_prompt"):
        if not str(prompt_data.get(field, "")).strip():
            errors.append(f"Campo obrigatório ausente ou vazio: {field}")

    system_prompt = str(prompt_data.get("system_prompt", ""))
    user_prompt = str(prompt_data.get("user_prompt", ""))

    if "{bug_report}" not in user_prompt:
        errors.append("user_prompt precisa conter a variável {bug_report}")

    if "[TODO]" in system_prompt or "[TODO]" in user_prompt:
        errors.append("Ainda há [TODO] no prompt")

    techniques = prompt_data.get("techniques_applied", [])
    if len(techniques) < 2:
        errors.append(f"Mínimo de 2 técnicas requeridas, encontradas: {len(techniques)}")

    return (len(errors) == 0, errors)


def main():
    """Função principal"""
    print_section_header("PUSH DO PROMPT OTIMIZADO (LangSmith Hub)")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    username = os.getenv("USERNAME_LANGSMITH_HUB", "").strip()

    data = load_yaml(PROMPT_FILE)
    if data is None:
        return 1

    prompt_data = data.get(PROMPT_KEY, data)

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido — corrija antes do push:")
        for erro in errors:
            print(f"   - {erro}")
        return 1

    prompt_name = f"{username}/{PROMPT_KEY}"
    print(f"Publicando: {prompt_name}")

    try:
        push_prompt_to_langsmith(prompt_name, prompt_data)
    except Exception as erro:
        print(f"❌ Falha no push: {erro}")
        print("Dica: o handle público só existe depois de tornar um prompt público pela UI do LangSmith.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
