import asyncio

from app.agent import ToolCallAgent
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory


if __name__ == "__main__":
    agent = ToolCallAgent()

    flow = FlowFactory.create_flow(
        flow_type=FlowType.PLANNING,
        agents=agent,
    )

    result = asyncio.run(
        flow.execute("Create a web app that shows Japan travel destinations")
    )
    print(result)
