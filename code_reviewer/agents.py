from google.adk.agents import Agent
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.models.google_llm import Gemini
from google.adk.sessions import DatabaseSessionService
from google.adk.sessions import InMemorySessionService, Session
from google.adk.runners import Runner
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from google.adk.tools import google_search
from .count_invocation_plugin import CountInvocationPlugin

SUMMARY_SYSTEM_PROMPT = """
You are a code review summarizer. Summarize the provided reviews into a single review. Provide the summary as markdown.
"""

MODEL_NAME = "gemini-2.5-flash-lite"
USER_ID = "default"

retry_config = types.HttpRetryOptions(
        attempts=5,  # Maximum retry attempts
        exp_base=7,  # Delay multiplier
        initial_delay=1,
        http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
    )

async def run_session(
    runner_instance: Runner,
    session_service: InMemorySessionService,
    user_queries: list[str] | str | None = None,
    session_name: str = "default",
) -> str:
    """
    Run a session with the given runner and user queries.

    Args:
        runner_instance (Runner): The runner instance to use.
        session_service (InMemorySessionService): The session service to use.
        user_queries (list[str] | str | None): The user queries to run.
        session_name (str): The session name to use.

    Returns:
        str: The response from the runner.
    """
    response = ""
    # Get app name from the Runner
    app_name = runner_instance.app_name

    # Attempt to create a new session or retrieve an existing one
    session: Session | None = None
    try:
        session = await session_service.create_session(
            app_name=app_name, user_id=USER_ID, session_id=session_name
        )
    except:
        session = await session_service.get_session(
            app_name=app_name, user_id=USER_ID, session_id=session_name
        )

    # Process queries if provided
    if user_queries:
        # Convert single query to list for uniform processing
        if type(user_queries) == str:
            user_queries = [user_queries]

        # Process each query in the list sequentially
        for query in user_queries:
            # Convert the query string to the ADK Content format
            queryContent = types.Content(role="user", parts=[types.Part(text=query)])
            
            # Stream the agent's response asynchronously
            async for event in runner_instance.run_async(
                user_id=USER_ID, session_id=session.id, new_message=queryContent  # type: ignore
            ):
                # Check if the event contains valid content
                if event.content and event.content.parts:
                    # Filter out empty or "None" responses before printing
                    if (
                        event.content.parts[0].text != "None"
                        and event.content.parts[0].text
                    ):
                        response += event.content.parts[0].text

    return response

class ReviewAgent:
    REVIEW_SYSTEM_PROMPT = """
You are an AI code review assistant. Review ONLY the provided diff hunk. If there is something you don't understand, use the search tool to look it up.
- Identify correctness issues
- Spot bugs
- Flag style/consistency problems
- Suggest improvements
Be specific and concise.
"""
    def __init__(self):
        self.agent = Agent(
            model=Gemini(model=MODEL_NAME, retry_options=retry_config),
            name="code_review_bot",
            description="A code review bot",
            tools=[google_search],
            instruction=self.REVIEW_SYSTEM_PROMPT,
        )

        self.code_review_app_compacting = App(
            name="code_review_app_compacting",
            root_agent=review_agent,
            events_compaction_config=EventsCompactionConfig(
                compaction_interval=3,  # Trigger compaction every 3 invocations
                overlap_size=1,  # Keep 1 previous turn for context
            ),
            plugins=[CountInvocationPlugin()],
        )
        
        self.session_service = InMemorySessionService()

        # Create a new runner for our upgraded app
        self.code_review_runner_compacting = Runner(
            app=self.code_review_app_compacting, session_service=self.session_service
        )

    async def review(self, hunk: str) -> str:
        """
        Review a diff hunk.

        Args:
            hunk (str): The diff hunk to review.

        Returns:
            str: The review.
        """
        resp = await run_session(
            self.code_review_runner_compacting,
            self.session_service,
            f"Here is a diff hunk:\n```\n{hunk}\n```\nProvide the review:",
            "code_review",
        )

        return resp


async def summarise_reviews(reviews: list[str]) -> str:
    """
    Summarise a list of reviews into a single review.

    Args:
        reviews (list[str]): The reviews to summarise.

    Returns:
        str: The summary.
    """
    summary_agent = Agent(
        model=Gemini(model=MODEL_NAME, retry_options=retry_config),
        name="code_review_bot",
        description="A code review summarizer bot",
        instruction=SUMMARY_SYSTEM_PROMPT,
    )

    session_service = InMemorySessionService()
    runner = Runner(agent=summary_agent, session_service=session_service, app_name="default", plugins=[CountInvocationPlugin()])

    resp = await run_session(
        runner,
        session_service,
        f"Here are the reviews:\n```{reviews}\n```, provide a summary:",
        "code_review",
    )

    return resp