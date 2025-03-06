from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Union

from app.agent.base import BaseAgent
from app.agent.toolcall import ToolCallAgent


class FlowType(str, Enum):
    PLANNING = "planning"


class BaseFlow(ABC):
    """Base class for execution flows supporting multiple agents"""

    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **kwargs
    ):
        # Handle different ways of providing agents
        if isinstance(agents, BaseAgent):
            self.agents = {"default": agents}
        elif isinstance(agents, list):
            self.agents = {f"agent_{i}": agent for i, agent in enumerate(agents)}
        else:
            self.agents = agents

        self.tools = kwargs.get("tools")
        self.primary_agent_key = kwargs.get("primary_agent", None)

        # If primary agent not specified, use first agent
        if not self.primary_agent_key and self.agents:
            self.primary_agent_key = next(iter(self.agents))

        self._setup_agents()

    def _setup_agents(self):
        """Configure all agents with tools and initial setup"""
        if self.tools:
            for agent_key, agent in self.agents.items():
                if isinstance(agent, ToolCallAgent):
                    agent.available_tools = self.tools

    @property
    def primary_agent(self) -> Optional[BaseAgent]:
        """Get the primary agent for the flow"""
        return self.agents.get(self.primary_agent_key)

    def get_agent(self, key: str) -> Optional[BaseAgent]:
        """Get a specific agent by key"""
        return self.agents.get(key)

    def add_agent(self, key: str, agent: BaseAgent) -> None:
        """Add a new agent to the flow"""
        self.agents[key] = agent
        if isinstance(agent, ToolCallAgent) and self.tools:
            agent.available_tools = self.tools

    @abstractmethod
    async def execute(self, input_text: str) -> str:
        """Execute the flow with given input"""
