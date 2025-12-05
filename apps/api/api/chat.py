"""Chat endpoint for PM Copilot agent."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.database import get_db
from apps.api.services.pm_agent import get_pm_agent

router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str  # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str
    selected_insight_id: Optional[str] = None
    conversation_history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Chat with PM Copilot agent.

    Args:
        request: Chat request with message and optional context
        db: Database session

    Returns:
        AI-generated response
    """
    agent = get_pm_agent()

    # Convert conversation history to dict format
    history = None
    if request.conversation_history:
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]

    # Generate response
    response_text = agent.chat(
        user_message=request.message,
        db=db,
        selected_insight_id=request.selected_insight_id,
        conversation_history=history,
    )

    return ChatResponse(response=response_text)
