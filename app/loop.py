from typing import List, Optional

from app.agent.base import BaseAgent
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory
from app.tool import BaseTool, ToolCollection


async def loop(
    agent: BaseAgent,
    tools: Optional[List[BaseTool]] = None,
    flow_type: FlowType = FlowType.PLANNING,
    input_text: str = "",
    **loop_kwargs,
) -> str:
    """Main entry point for running an agent with specified flow type"""
    tool_collection = ToolCollection(*tools) if tools else None
    flow = FlowFactory.create_flow(
        flow_type, agent, tool_collection=tool_collection, **loop_kwargs
    )
    return await flow.execute(input_text)
