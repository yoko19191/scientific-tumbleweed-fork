"""CRUD API for custom agents."""

import logging

import opendal.exceptions as opendal_exc
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.gateway.deps import get_current_user_id
from deerflow.config.agents_config import AgentConfig, CustomAgentStore, normalize_agent_name, validate_agent_name
from deerflow.storage import (
    get_async_operator,
    user_profile_key,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["agents"])


def _is_opendal_not_found(exc: BaseException) -> bool:
    """Return True if the OpenDAL error represents a missing object.

    OpenDAL 0.47 raises ``opendal.exceptions.NotFound`` directly; older
    releases sometimes bubbled up a plain ``FileNotFoundError`` from the
    filesystem backend. Cover both.
    """
    return isinstance(exc, (opendal_exc.NotFound, FileNotFoundError))


class AgentResponse(BaseModel):
    """Response model for a custom agent."""

    name: str = Field(..., description="Agent name (hyphen-case)")
    description: str = Field(default="", description="Agent description")
    model: str | None = Field(default=None, description="Optional model override")
    tool_groups: list[str] | None = Field(default=None, description="Optional tool group whitelist")
    soul: str | None = Field(default=None, description="SOUL.md content")


class AgentsListResponse(BaseModel):
    """Response model for listing all custom agents."""

    agents: list[AgentResponse]


class AgentCreateRequest(BaseModel):
    """Request body for creating a custom agent."""

    name: str = Field(..., description="Agent name (must match ^[A-Za-z0-9-]+$, stored as lowercase)")
    description: str = Field(default="", description="Agent description")
    model: str | None = Field(default=None, description="Optional model override")
    tool_groups: list[str] | None = Field(default=None, description="Optional tool group whitelist")
    soul: str = Field(default="", description="SOUL.md content — agent personality and behavioral guardrails")


class AgentUpdateRequest(BaseModel):
    """Request body for updating a custom agent."""

    description: str | None = Field(default=None, description="Updated description")
    model: str | None = Field(default=None, description="Updated model override")
    tool_groups: list[str] | None = Field(default=None, description="Updated tool group whitelist")
    soul: str | None = Field(default=None, description="Updated SOUL.md content")


def _validate_agent_name(name: str) -> None:
    """Validate agent name against allowed pattern.

    Args:
        name: The agent name to validate.

    Raises:
        HTTPException: 422 if the name is invalid.
    """
    try:
        validate_agent_name(name)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


def _normalize_agent_name(name: str) -> str:
    """Normalize agent name to lowercase for filesystem storage."""
    return normalize_agent_name(name)


def _agent_config_to_response(agent_cfg: AgentConfig, include_soul: bool = False, user_id: str | None = None) -> AgentResponse:
    """Convert AgentConfig to AgentResponse."""
    soul: str | None = None
    if include_soul:
        soul = CustomAgentStore().load_soul(agent_cfg.name, user_id=user_id) or ""

    return AgentResponse(
        name=agent_cfg.name,
        description=agent_cfg.description,
        model=agent_cfg.model,
        tool_groups=agent_cfg.tool_groups,
        soul=soul,
    )


@router.get(
    "/agents",
    response_model=AgentsListResponse,
    summary="List Custom Agents",
    description="List all custom agents available in the agents directory, including their soul content.",
)
async def list_agents(user_id: str = Depends(get_current_user_id)) -> AgentsListResponse:
    """List all custom agents.

    Returns:
        List of all custom agents with their metadata and soul content.
    """
    try:
        agents = CustomAgentStore().list_agents(user_id=user_id)
        return AgentsListResponse(agents=[_agent_config_to_response(a, include_soul=True, user_id=user_id) for a in agents])
    except Exception as e:
        logger.error(f"Failed to list agents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@router.get(
    "/agents/check",
    summary="Check Agent Name",
    description="Validate an agent name and check if it is available (case-insensitive).",
)
async def check_agent_name(name: str, user_id: str = Depends(get_current_user_id)) -> dict:
    """Check whether an agent name is valid and not yet taken."""
    _validate_agent_name(name)
    normalized = _normalize_agent_name(name)
    available = not CustomAgentStore().exists(normalized, user_id)
    return {"available": available, "name": normalized}


class UserProfileResponse(BaseModel):
    """Response model for the global user profile (USER.md)."""

    content: str | None = Field(default=None, description="USER.md content, or null if not yet created")


class UserProfileUpdateRequest(BaseModel):
    """Request body for setting the global user profile."""

    content: str = Field(default="", description="USER.md content — describes the user's background and preferences")


# NOTE: the user-profile routes must be declared BEFORE /agents/{name}
# so FastAPI's path matcher does not interpret ``user-profile`` as an
# agent name. Moving the handlers out of registration order broke the
# original placement in Round 2.1 — keep them here.


@router.get(
    "/agents/user-profile",
    response_model=UserProfileResponse,
    summary="Get User Profile",
    description="Read the global USER.md file that is injected into all custom agents.",
)
async def get_user_profile(user_id: str = Depends(get_current_user_id)) -> UserProfileResponse:
    """Return the current USER.md content."""
    try:
        operator = get_async_operator()
        key = user_profile_key(user_id)
        try:
            raw_bytes = await operator.read(key)
        except Exception as exc:
            if _is_opendal_not_found(exc):
                return UserProfileResponse(content=None)
            raise
        content = bytes(raw_bytes).decode("utf-8").strip()
        return UserProfileResponse(content=content or None)
    except Exception as e:
        logger.error(f"Failed to read user profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read user profile: {str(e)}")


@router.put(
    "/agents/user-profile",
    response_model=UserProfileResponse,
    summary="Update User Profile",
    description="Write the global USER.md file that is injected into all custom agents.",
)
async def update_user_profile(body: UserProfileUpdateRequest, user_id: str = Depends(get_current_user_id)) -> UserProfileResponse:
    """Create or overwrite USER.md."""
    try:
        operator = get_async_operator()
        key = user_profile_key(user_id)
        await operator.write(key, body.content.encode("utf-8"))
        logger.info("Updated USER.md at %s", key)
        return UserProfileResponse(content=body.content or None)
    except Exception as e:
        logger.error(f"Failed to update user profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update user profile: {str(e)}")


@router.get(
    "/agents/{name}",
    response_model=AgentResponse,
    summary="Get Custom Agent",
    description="Retrieve details and SOUL.md content for a specific custom agent.",
)
async def get_agent(name: str, user_id: str = Depends(get_current_user_id)) -> AgentResponse:
    """Get a specific custom agent by name."""
    _validate_agent_name(name)
    name = _normalize_agent_name(name)

    try:
        agent_cfg = CustomAgentStore().load_config(name, user_id=user_id)
        return _agent_config_to_response(agent_cfg, include_soul=True, user_id=user_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    except Exception as e:
        logger.error(f"Failed to get agent '{name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")


@router.post(
    "/agents",
    response_model=AgentResponse,
    status_code=201,
    summary="Create Custom Agent",
    description="Create a new custom agent with its config and SOUL.md.",
)
async def create_agent_endpoint(body: AgentCreateRequest, user_id: str = Depends(get_current_user_id)) -> AgentResponse:
    """Create a new custom agent."""
    _validate_agent_name(body.name)
    normalized_name = _normalize_agent_name(body.name)

    store = CustomAgentStore()
    if store.exists(normalized_name, user_id):
        raise HTTPException(status_code=409, detail=f"Agent '{normalized_name}' already exists")

    try:
        agent_cfg = store.create_agent(
            AgentConfig(
                name=normalized_name,
                description=body.description,
                model=body.model,
                tool_groups=body.tool_groups,
            ),
            body.soul,
            user_id=user_id,
        )
        logger.info("Created agent '%s'", normalized_name)
        return _agent_config_to_response(agent_cfg, include_soul=True, user_id=user_id)

    except HTTPException:
        raise
    except FileExistsError:
        raise HTTPException(status_code=409, detail=f"Agent '{normalized_name}' already exists")
    except Exception as e:
        logger.error(f"Failed to create agent '{body.name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@router.put(
    "/agents/{name}",
    response_model=AgentResponse,
    summary="Update Custom Agent",
    description="Update an existing custom agent's config and/or SOUL.md.",
)
async def update_agent(name: str, body: AgentUpdateRequest, user_id: str = Depends(get_current_user_id)) -> AgentResponse:
    """Update an existing custom agent."""
    _validate_agent_name(name)
    name = _normalize_agent_name(name)

    try:
        store = CustomAgentStore()
        agent_cfg = store.load_config(name, user_id=user_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    try:
        # Update config if any config fields changed
        config_changed = any(v is not None for v in [body.description, body.model, body.tool_groups])

        if config_changed:
            store.write_config(
                AgentConfig(
                    name=agent_cfg.name,
                    description=body.description if body.description is not None else agent_cfg.description,
                    model=body.model if body.model is not None else agent_cfg.model,
                    tool_groups=body.tool_groups if body.tool_groups is not None else agent_cfg.tool_groups,
                    skills=agent_cfg.skills,
                ),
                user_id=user_id,
            )

        # Update SOUL.md if provided
        if body.soul is not None:
            store.write_soul(name, body.soul, user_id=user_id)

        logger.info(f"Updated agent '{name}'")

        refreshed_cfg = store.load_config(name, user_id=user_id)
        return _agent_config_to_response(refreshed_cfg, include_soul=True, user_id=user_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent '{name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {str(e)}")


@router.delete(
    "/agents/{name}",
    status_code=204,
    summary="Delete Custom Agent",
    description="Delete a custom agent and all its files (config, SOUL.md, memory).",
)
async def delete_agent(name: str, user_id: str = Depends(get_current_user_id)) -> None:
    """Delete a custom agent."""
    _validate_agent_name(name)
    name = _normalize_agent_name(name)

    store = CustomAgentStore()
    if not store.exists(name, user_id):
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    try:
        removed = store.delete_agent(name, user_id)
        logger.info("Deleted agent '%s' (removed %d objects)", name, removed)
    except Exception as e:
        logger.error(f"Failed to delete agent '{name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")
