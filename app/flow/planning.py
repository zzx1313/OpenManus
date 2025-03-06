import time
from typing import Dict, List, Optional, Union

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow
from app.logger import logger
from app.schema import AgentState
from app.tool import PlanningTool, ToolCollection


class PlanningFlow(BaseFlow):
    """A flow that manages planning and execution of tasks using agents."""

    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **kwargs
    ):
        # Initialize planning tool first
        self.planning_tool = self._initialize_planning_tool(kwargs.get("tools"))

        # If tools were provided, ensure planning tool is included
        tools = kwargs.get("tools")
        if tools:
            planning_tool_exists = any(
                isinstance(tool, PlanningTool) for tool in tools.tools
            )
            if not planning_tool_exists:
                tools.add_tool(self.planning_tool)
        else:
            # Create a new tool collection with at least the planning tool
            tools = ToolCollection(self.planning_tool)
            kwargs["tools"] = tools

        super().__init__(agents, **kwargs)

        # Define agent roles
        self.planner_key = kwargs.get("planner", self.primary_agent_key)
        self.executor_keys = kwargs.get("executors", list(self.agents.keys()))

        # Planning state tracking
        self.active_plan_id = kwargs.get("plan_id", f"plan_{int(time.time())}")
        self.current_step_index = None

        # Ensure the planning tool has been initialized properly
        if not hasattr(self.planning_tool, "_plans"):
            self.planning_tool._plans = {}

    def _initialize_planning_tool(
        self, tools: Optional[ToolCollection]
    ) -> PlanningTool:
        """Initialize planning tool, reusing existing one if available"""
        if tools:
            for tool in tools.tools:
                if isinstance(tool, PlanningTool):
                    return tool
        return PlanningTool()

    @property
    def planner(self) -> Optional[BaseAgent]:
        """Get the planning agent"""
        return (
            self.agents.get(self.planner_key)
            if self.planner_key
            else self.primary_agent
        )

    def get_executor(self, step_type: Optional[str] = None) -> BaseAgent:
        """
        Get an appropriate executor agent for the current step.
        Can be extended to select agents based on step type/requirements.
        """
        # If step type is provided and matches an agent key, use that agent
        if step_type and step_type in self.agents:
            return self.agents[step_type]

        # Otherwise use the first available executor or fall back to primary agent
        for key in self.executor_keys:
            if key in self.agents:
                return self.agents[key]

        # Fallback to primary agent
        return self.primary_agent

    async def execute(self, input_text: str) -> str:
        """Execute the planning flow with agents."""
        try:
            if not self.primary_agent:
                raise ValueError("No primary agent available")

            # Create initial plan if input provided
            if input_text:
                await self._create_initial_plan(input_text)

                # Verify plan was created successfully
                if self.active_plan_id not in self.planning_tool._plans:
                    logger.error(
                        f"Plan creation failed. Plan ID {self.active_plan_id} not found in planning tool."
                    )
                    return f"Failed to create plan for: {input_text}"

            result = ""
            while True:
                # Get current step to execute
                self.current_step_index, step_info = await self._get_current_step_info()

                # Exit if no more steps or plan completed
                if self.current_step_index is None:
                    result += await self._finalize_plan()
                    break

                # Execute current step with appropriate agent
                step_type = step_info.get("type") if step_info else None
                executor = self.get_executor(step_type)
                step_result = await self._execute_step(executor, step_info)
                result += step_result + "\n"

                # Check if agent wants to terminate
                if hasattr(executor, "state") and executor.state == AgentState.FINISHED:
                    break

            return result
        except Exception as e:
            logger.error(f"Error in PlanningFlow: {str(e)}")
            return f"Execution failed: {str(e)}"

    async def _create_initial_plan(self, request: str) -> None:
        """Create an initial plan based on the request using an appropriate agent."""
        logger.info(f"Creating initial plan with ID: {self.active_plan_id}")

        agent = self.planner if self.planner else self.primary_agent

        # First, directly create an empty plan to ensure the plan ID exists
        self.planning_tool._plans[self.active_plan_id] = {
            "title": f"Plan for: {request[:50]}{'...' if len(request) > 50 else ''}",
            "description": f"Auto-generated plan for request: {request}",
            "steps": [],
            "step_status": {},
            "created_at": time.time(),
            "updated_at": time.time(),
        }

        # Use agent.run to create the plan
        plan_prompt = f"""
        I need you to create a detailed plan to accomplish this task:

        {request}

        Please create a plan with ID {self.active_plan_id} using the planning tool.
        The plan should include all necessary steps to complete the task.
        """

        try:
            plan_result = await agent.run(plan_prompt)
            logger.info(f"Plan creation result: {plan_result[:200]}...")

            # Verify the plan was created
            if (
                self.active_plan_id not in self.planning_tool._plans
                or not self.planning_tool._plans[self.active_plan_id].get("steps")
            ):
                logger.warning(
                    "Plan may not have been created properly. Creating default plan."
                )
                await self._create_default_plan(request)
        except Exception as e:
            logger.error(f"Error creating plan: {e}")
            await self._create_default_plan(request)

    async def _create_default_plan(self, request: str) -> None:
        """Create a default plan if the agent fails to create one."""
        try:
            # Try using the planning tool directly
            await self.planning_tool.execute(
                command="create",
                plan_id=self.active_plan_id,
                title=f"Plan for: {request[:50]}{'...' if len(request) > 50 else ''}",
                description=f"Auto-generated plan for request: {request}",
                steps=["Analyze request", "Execute task", "Verify results"],
            )
        except Exception as e:
            logger.error(f"Failed to create default plan with planning tool: {e}")
            # Create plan directly in the planning tool's storage
            self.planning_tool._plans[self.active_plan_id] = {
                "title": f"Emergency Plan for: {request[:50]}{'...' if len(request) > 50 else ''}",
                "description": f"Emergency auto-generated plan for request: {request}",
                "steps": ["Analyze request", "Execute task", "Verify results"],
                "step_status": {
                    "0": "not_started",
                    "1": "not_started",
                    "2": "not_started",
                },
                "created_at": time.time(),
                "updated_at": time.time(),
            }

        logger.info(f"Created default plan with ID: {self.active_plan_id}")

    async def _get_current_step_info(self) -> tuple[Optional[int], Optional[dict]]:
        """
        Parse the current plan to identify the first non-completed step's index and info.
        Returns (None, None) if no active step is found.
        """
        if (
            not self.active_plan_id
            or self.active_plan_id not in self.planning_tool._plans
        ):
            logger.error(f"Plan with ID {self.active_plan_id} not found")
            return None, None

        try:
            # Direct access to step status from planning tool storage
            plan_data = self.planning_tool._plans[self.active_plan_id]
            steps = plan_data.get("steps", [])
            step_status = plan_data.get("step_status", {})

            # Find first non-completed step
            for i, step in enumerate(steps):
                status = step_status.get(str(i), "not_started")
                if status in ["not_started", "in_progress"]:
                    # Extract step type/category if available
                    step_info = {"text": step}

                    # Try to extract step type from the text (e.g., [SEARCH] or [CODE])
                    import re

                    type_match = re.search(r"\[([A-Z_]+)\]", step)
                    if type_match:
                        step_info["type"] = type_match.group(1).lower()

                    # Mark current step as in_progress
                    try:
                        await self.planning_tool.execute(
                            command="mark_step",
                            plan_id=self.active_plan_id,
                            step_index=i,
                            step_status="in_progress",
                        )
                    except Exception as e:
                        logger.warning(f"Error marking step as in_progress: {e}")
                        # Update step status directly
                        step_status[str(i)] = "in_progress"
                        plan_data["step_status"] = step_status
                        plan_data["updated_at"] = time.time()

                    return i, step_info

            return None, None  # No active step found

        except Exception as e:
            logger.warning(f"Error finding current step index: {e}")
            return None, None

    async def _execute_step(self, executor: BaseAgent, step_info: dict) -> str:
        """Execute the current step with the specified agent using agent.run()."""
        # Prepare context for the agent with current plan status
        plan_status = await self._get_plan_text()
        step_text = step_info.get("text", f"Step {self.current_step_index}")

        # Create a prompt for the agent to execute the current step
        step_prompt = f"""
        CURRENT PLAN STATUS:
        {plan_status}

        YOUR CURRENT TASK:
        You are now working on step {self.current_step_index}: "{step_text}"

        Please execute this step using the appropriate tools. When you're done, provide a summary of what you accomplished.
        """

        # Use agent.run() to execute the step
        try:
            step_result = await executor.run(step_prompt)

            # Mark the step as completed after successful execution
            await self._mark_step_completed()

            return step_result
        except Exception as e:
            logger.error(f"Error executing step {self.current_step_index}: {e}")
            return f"Error executing step {self.current_step_index}: {str(e)}"

    async def _mark_step_completed(self) -> None:
        """Mark the current step as completed."""
        if self.current_step_index is None:
            return

        try:
            # Mark the step as completed
            await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=self.current_step_index,
                step_status="completed",
            )
            logger.info(
                f"Marked step {self.current_step_index} as completed in plan {self.active_plan_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to update plan status: {e}")
            # Update step status directly in planning tool storage
            if self.active_plan_id in self.planning_tool._plans:
                plan_data = self.planning_tool._plans[self.active_plan_id]
                step_status = plan_data.get("step_status", {})
                step_status[str(self.current_step_index)] = "completed"
                plan_data["step_status"] = step_status
                plan_data["updated_at"] = time.time()

    async def _get_plan_text(self) -> str:
        """Get the current plan as formatted text."""
        try:
            result = await self.planning_tool.execute(
                command="get", plan_id=self.active_plan_id
            )
            return result.output if hasattr(result, "output") else str(result)
        except Exception as e:
            logger.error(f"Error getting plan: {e}")
            return self._generate_plan_text_from_storage()

    def _generate_plan_text_from_storage(self) -> str:
        """Generate plan text directly from storage if the planning tool fails."""
        try:
            if self.active_plan_id not in self.planning_tool._plans:
                return f"Error: Plan with ID {self.active_plan_id} not found"

            plan_data = self.planning_tool._plans[self.active_plan_id]
            title = plan_data.get("title", "Untitled Plan")
            description = plan_data.get("description", "")
            steps = plan_data.get("steps", [])
            step_status = plan_data.get("step_status", {})

            # Count steps by status
            status_counts = {
                "completed": 0,
                "in_progress": 0,
                "blocked": 0,
                "not_started": 0,
            }
            for status in step_status.values():
                if status in status_counts:
                    status_counts[status] += 1

            completed = status_counts["completed"]
            total = len(steps)
            progress = (completed / total) * 100 if total > 0 else 0

            plan_text = f"Plan: {title} (ID: {self.active_plan_id})\n"
            plan_text += "=" * len(plan_text) + "\n\n"
            plan_text += f"{description}\n\n" if description else ""
            plan_text += (
                f"Progress: {completed}/{total} steps completed ({progress:.1f}%)\n"
            )
            plan_text += f"Status: {status_counts['completed']} completed, {status_counts['in_progress']} in progress, "
            plan_text += f"{status_counts['blocked']} blocked, {status_counts['not_started']} not started\n\n"
            plan_text += "Steps:\n"

            for i, step in enumerate(steps):
                status = step_status.get(str(i), "not_started")
                if status == "completed":
                    status_mark = "[✓]"
                elif status == "in_progress":
                    status_mark = "[→]"
                elif status == "blocked":
                    status_mark = "[!]"
                else:  # not_started
                    status_mark = "[ ]"

                plan_text += f"{i}. {status_mark} {step}\n"

            return plan_text
        except Exception as e:
            logger.error(f"Error generating plan text from storage: {e}")
            return f"Error: Unable to retrieve plan with ID {self.active_plan_id}"

    async def _get_plan(self) -> dict:
        """Get the current plan as a dictionary."""
        if (
            not self.active_plan_id
            or self.active_plan_id not in self.planning_tool._plans
        ):
            return {}
        return self.planning_tool._plans[self.active_plan_id]

    async def _finalize_plan(self) -> str:
        """Finalize the plan and provide a summary using an appropriate agent."""
        agent = self.planner if self.planner else self.primary_agent
        plan_text = await self._get_plan_text()

        # Create a summary prompt
        summary_prompt = f"""
        The plan has been completed. Here is the final plan status:

        {plan_text}

        Please provide a summary of what was accomplished and any final thoughts.
        """

        # Use agent.run() to generate the summary
        try:
            summary = await agent.run(summary_prompt)
            return f"Plan completed:\n\n{summary}"
        except Exception as e:
            logger.error(f"Error finalizing plan: {e}")
            return "Plan completed. Error generating summary."
