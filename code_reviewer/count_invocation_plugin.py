import logging
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.adk.models.llm_request import LlmRequest
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.base_tool import BaseTool
from typing import Any

# Applies to all agent and model calls
class CountInvocationPlugin(BasePlugin):
    """A custom plugin that counts agent and tool invocations."""

    def __init__(self) -> None:
        """Initialize the plugin with counters."""
        super().__init__(name="count_invocation")
        self.agent_count: int = 0
        self.tool_count: int = 0
        self.llm_request_count: int = 0
        self.total_token_count: int = 0

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> None:
        """Count agent runs."""
        self.agent_count += 1
        logging.info(f"[CountInvocationPlugin] Agent run count: {self.agent_count}")

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> None:
        """Count LLM requests."""
        self.llm_request_count += 1
        logging.info(f"[CountInvocationPlugin] LLM request count: {self.llm_request_count}")

    async def after_model_callback(self, *, callback_context: CallbackContext, llm_response: LlmResponse) -> None:
        if llm_response.usage_metadata is not None and llm_response.usage_metadata.total_token_count is not None:
            self.total_token_count += llm_response.usage_metadata.total_token_count
        logging.info(f"[CountInvocationPlugin] Total token count: {self.total_token_count}")

    async def before_tool_callback(
        self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext
    ) -> None:
        """Count tool runs."""
        self.tool_count += 1
        logging.info(f"[CountInvocationPlugin] Tool run count: {self.tool_count}")