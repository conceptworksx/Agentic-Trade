# agents/base_agent.py

import yaml
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from config.settings import get_llm
from core.error import handle_llm_errors
from core.logging import get_logger
logger = get_logger(__name__)

def load_structured_prompt(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Prompt file missing at {file_path}")
    with open(path, "r") as file:
        data = yaml.safe_load(file)
    return yaml.dump(data, sort_keys=False, allow_unicode=True)


class BaseAgent:
    """
    Every agent inherits this.
    Child class only needs to define:
      - prompt_path   : path to its yaml prompt
      - tools         : list of LangChain tools it can use
      - run()         : its own input signature matching what nodes.py passes
    """

    prompt_path: str = ""          # override in child
    tools: list = []               # override in child

    def __init__(self):
        self.llm            = get_llm()
        self.tool_executor  = ToolNode(tools=self.tools) if self.tools else None

        yaml_instructions   = load_structured_prompt(self.prompt_path)
        tool_names          = ", ".join([t.__name__ for t in self.tools]) if self.tools else "None"

        system_instructions = (
            "### CORE PROTOCOL ###\n"
            f"{yaml_instructions}\n"
            "---\n"
            "### EXECUTION ENVIRONMENT ###\n"
            f"- Available Tools: {tool_names}\n"
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_instructions),
            MessagesPlaceholder(variable_name="messages"),
        ])

        self.chain = self.prompt | self.llm.bind_tools(self.tools) \
                     if self.tools else self.prompt | self.llm


    @handle_llm_errors(retries=1)
    def _invoke(self, messages: list, **kwargs) -> str:
        """
        Core loop: call LLM → execute tools if needed → repeat → return final string.
        Every child calls this inside their own run() method.
        """
        while True:
            
            # now the prompt is no more static takes the input from the run() where self._invoke() is called
            invoke_payload={"messages": messages}
            invoke_payload.update(kwargs)

            result: AIMessage = self.chain.invoke(invoke_payload)
            messages.append(result)

            if not result.tool_calls:
                return result.content           # final answer — return to nodes.py

            if self.tool_executor is None:
                return result.content           # no tools registered, return as-is

            tool_response = self.tool_executor.invoke({"messages": [result]})
            tool_message: ToolMessage = tool_response["messages"][-1]
            messages.append(tool_message)       # feed result back, loop again

  
    def run(self, *args, **kwargs):
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement run()"
        )