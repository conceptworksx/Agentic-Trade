import yaml
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from config.settings import get_llm


def load_structured_prompt(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Prompt file missing at {file_path}")
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return yaml.dump(data, sort_keys=False, allow_unicode=True)


class BaseAgent:
    """
    Provides shared setup for all agents:
      - LLM instance via get_llm()
      - Prompt loading from YAML
      - Enforces run() interface

    Each child class defines its own full chain in __init__
    and implements run() with its own input signature.
    """

    prompt_path: str = ""

    def __init__(self):
        self.llm = get_llm()

        yaml_instructions = load_structured_prompt(self.prompt_path)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", yaml_instructions),
            MessagesPlaceholder(variable_name="messages"),
        ])

    def run(self, *args, **kwargs):
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement run()"
        )