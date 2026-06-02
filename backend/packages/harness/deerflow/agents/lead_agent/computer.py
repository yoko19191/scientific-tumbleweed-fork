"""Computer lead-agent entrypoint."""

from langchain_core.runnables import RunnableConfig

from deerflow.agents.lead_agent.base import build_lead_agent
from deerflow.agents.lead_agent.config import COMPUTER_PROFILE


def make_computer_lead_agent(config: RunnableConfig):
    return build_lead_agent(COMPUTER_PROFILE, config)
