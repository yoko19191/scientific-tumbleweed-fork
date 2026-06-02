from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.gateway.thread_ownership import require_thread_owner
from deerflow.agents.suggestion_agent import (
    _extract_response_text,
    _format_conversation,
    _parse_json_string_list,
    _strip_markdown_code_fence,
)
from deerflow.agents.suggestion_agent import (
    generate_suggestions as _generate_suggestions,
)
from deerflow.models import create_chat_model

router = APIRouter(prefix="/api", tags=["suggestions"])

__all__ = [
    "SuggestionsRequest",
    "SuggestionsResponse",
    "SuggestionMessage",
    "_extract_response_text",
    "_format_conversation",
    "_parse_json_string_list",
    "_strip_markdown_code_fence",
    "generate_suggestions",
    "router",
]


class SuggestionMessage(BaseModel):
    role: str = Field(..., description="Message role: user|assistant")
    content: str = Field(..., description="Message content as plain text")


class SuggestionsRequest(BaseModel):
    messages: list[SuggestionMessage] = Field(..., description="Recent conversation messages")
    n: int = Field(default=3, ge=1, le=5, description="Number of suggestions to generate")
    model_name: str | None = Field(default=None, description="Optional model override")


class SuggestionsResponse(BaseModel):
    suggestions: list[str] = Field(default_factory=list, description="Suggested follow-up questions")


@router.post(
    "/threads/{thread_id}/suggestions",
    response_model=SuggestionsResponse,
    summary="Generate Follow-up Questions",
    description="Generate short follow-up questions a user might ask next, based on recent conversation context.",
)
async def generate_suggestions(thread_id: str, request: Request, body: SuggestionsRequest) -> SuggestionsResponse:
    await require_thread_owner(request, thread_id)

    if not body.messages:
        return SuggestionsResponse(suggestions=[])

    suggestions = await _generate_suggestions(
        body.messages,
        body.n,
        body.model_name,
        model_factory=create_chat_model,
    )
    return SuggestionsResponse(suggestions=suggestions)
