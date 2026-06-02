"""Chat lead-agent entrypoint."""

from langchain_core.runnables import RunnableConfig

from deerflow.agents.lead_agent.base import build_lead_agent
from deerflow.agents.lead_agent.config import CHAT_PROFILE


def make_chat_lead_agent(config: RunnableConfig):
    return build_lead_agent(CHAT_PROFILE, config)
