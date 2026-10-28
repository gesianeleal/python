"""
Testes automatizados para validação de prompts.
"""
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
V2_PATH = PROMPTS_DIR / "bug_to_user_story_v2.yml"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt_data():
    """Dados do prompt otimizado (v2), já sem a chave raiz."""
    data = load_prompts(str(V2_PATH))
    assert data, f"YAML vazio ou inválido: {V2_PATH}"
    return data.get("bug_to_user_story_v2", data)


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt_data):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        system_prompt = prompt_data.get("system_prompt", "")
        assert isinstance(system_prompt, str) and system_prompt.strip(), \
            "system_prompt ausente ou vazio"

    def test_prompt_has_role_definition(self, prompt_data):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        texto = prompt_data.get("system_prompt", "").lower()
        assert "você é um" in texto or "você é uma" in texto, \
            "persona não definida (esperado algo como 'Você é um Product Manager...')"

    def test_prompt_mentions_format(self, prompt_data):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        texto = prompt_data.get("system_prompt", "").lower()
        marcadores = ["user story", "critérios de aceitação", "markdown"]
        assert any(m in texto for m in marcadores), \
            "o prompt não exige formato de saída (User Story/Markdown)"

    def test_prompt_has_few_shot_examples(self, prompt_data):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        texto = prompt_data.get("system_prompt", "")
        assert "few-shot" in texto.lower(), "seção de Few-shot não encontrada no prompt"
        assert texto.count("Exemplo") >= 2, "menos de 2 exemplos de entrada/saída no prompt"

    def test_prompt_no_todos(self, prompt_data):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        texto = str(prompt_data.get("system_prompt", "")) + str(prompt_data.get("user_prompt", ""))
        assert "[TODO]" not in texto, "há [TODO] pendente no prompt"

    def test_minimum_techniques(self, prompt_data):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        tecnicas = prompt_data.get("techniques_applied", [])
        assert len(tecnicas) >= 2, f"mínimo de 2 técnicas; encontradas: {len(tecnicas)}"

    def test_prompt_structure_is_valid(self, prompt_data):
        """Extra: valida a estrutura completa com a função do utils oficial."""
        valido, erros = validate_prompt_structure(prompt_data)
        assert valido, f"estrutura inválida segundo utils.validate_prompt_structure: {erros}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
