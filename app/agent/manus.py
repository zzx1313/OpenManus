from pydantic import Field, model_validator

from app.agent.planning import PlanningAgent
from app.agent.toolcall_en import ToolCallAgent
from app.tool import ToolCollection, Bash, Terminate
from app.tool.planning import PlanningTool
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.google_search import GoogleSearch
from app.tool.python_execute import PythonExecute
from app.tool.file_saver import FileSaver

from app.prompt.manus import SYSTEM_PROMPT, NEXT_STEP_PROMPT


class Manus(ToolCallAgent):
    """
    A versatile general-purpose agent that uses planning to solve various tasks.

    This agent extends PlanningAgent with a comprehensive set of tools and capabilities,
    including Python execution, web browsing, file operations, and information retrieval
    to handle a wide range of user requests.
    """

    name: str = "Manus"
    description: str = "A versatile agent that can solve various tasks using multiple tools"

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    # Add general-purpose tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(), GoogleSearch(), BrowserUseTool(), FileSaver(), Terminate()
        )
    )

