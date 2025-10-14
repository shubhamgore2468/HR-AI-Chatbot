from __future__ import annotations

from typing import Dict, Optional, Any, List
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.core.logger import log
from app.database.database import get_db
from app.models.sessions import Session as DBSession
from app.models.message import Message as DBMessage
from app.models.hiring import HiringContext as DBHiringContext
from app.schemas.enums import SessionStatus, StepName, Sender, Role

from app.core.agent import build_graph

router = APIRouter()
agent = build_graph()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[UUID] = None

class ChatResponse(BaseModel):
    session_id: UUID
    response: str
    current_step: StepName
    hiring_context: Dict[str, Any] = Field(default_factory=dict)

class SessionSummary(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    current_step: StepName
    status: SessionStatus


#-------------------------------
# Helper functions
#-------------------------------

def _load_langchain_messages(db:Session, session_id:UUID) -> List[BaseMessage]:
    rows = (
        db.query(DBMessage)
        .filter(DBMessage.session_id == session_id)
        .order_by(DBMessage.created_at.asc())
    )

    out: List[BaseMessage] = []

    for r in rows:
        if r.role == Role.user.value:
            out.append(HumanMessage(content=r.content))
        else:
            out.append(AIMessage(content=r.content))
    return out

def _context_to_hiring_dict(ctx: Optional[DBHiringContext]) -> Dict[str, Any]:
    if not ctx:
        return {}
    return {
        "roles": [ctx.primary_role] if ctx.primary_role else [],
        "budget": ctx.budget,
        "timeline": ctx.timeline,
        "location": ctx.location,
        "experience_level": ctx.experience_level,
        "skills": ctx.skills_json or [],
        "extras": ctx.extras_json or {},
    }

def _upsert_hiring_context(db:Session,session_id: UUID,incoming: Dict[str, Any]) -> DBHiringContext:
    ctx = db.query(DBHiringContext).filter(DBHiringContext.session_id == session_id).first()
    roles = (incoming or {}).get("roles") or []
    primary_role = roles[0] if roles else None

    patch = {
        "primary_role": primary_role,
        "budget": incoming.get("budget"),
        "timeline": incoming.get("timeline"),
        "location": incoming.get("location"),
        "experience_level": incoming.get("experience_level"),
        "skills_json": incoming.get("skills"),
        "extras_json": incoming.get("extras"),
    }

    if ctx:
        for k,v in patch.items():
            if v is not None:
                setattr(ctx, k, v)
        return ctx
    else:
        new_ctx = DBHiringContext(session_id=session_id, **patch)
        db.add(new_ctx)
        return new_ctx


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """
    Chat entrypoint:
    - Ensure session exists
    - Persist user message
    - Invoke agent with normalized state
    - Persist AI reply
    - Upsert HiringContext
    - Update Session.current_step
    """
    # 1) Session (UUID end-to-end)
    sid: UUID = request.session_id or uuid4()
    log.info("Chat request received", extra={"session_id": str(sid), "msg_len": len(request.message), "Chat request type":type(request.message)})
    session_row = db.query(DBSession).filter(DBSession.id == sid).first()

    if not session_row:
        session_row = DBSession(
            id=sid,
            status=SessionStatus.active.value,
            current_step=StepName.start.value,
            context_json={},  # lightweight debug bag
        )
        db.add(session_row)
        db.flush()  # get PK early

    # 2) Load prior messages & persist the new user message BEFORE invoking agent
    prior_msgs = _load_langchain_messages(db, session_row.id)
    log.info("Loaded prior messages", extra={"count": len(prior_msgs), "prior_msgs" : type(prior_msgs) })

    user_msg = DBMessage(
        session_id=session_row.id,
        sender=Sender.user.value,
        role=Role.user.value,
        content=request.message,
        meta_json={},
    )
    db.add(user_msg)
    db.flush()

    prior_msgs.append(HumanMessage(content=request.message))

    # 3) Prepare agent state from normalized DB
    hiring_ctx = db.query(DBHiringContext).filter(DBHiringContext.session_id == session_row.id).first()
    agent_state = {
        "messages": prior_msgs,
        "hiring_data": _context_to_hiring_dict(hiring_ctx),
        "current_step": session_row.current_step,
        "session_id": str(session_row.id),  # if your graph expects str; otherwise keep UUID
    }

    # 4) Invoke agent
    try:
        result = agent.invoke(agent_state)
        log.info("Agent invoked successfully", extra={"result_keys": list(result.keys()), "result": result, "type": type(result), "result.messages" : result.messages})
        # 5) Extract AI response safely
        msgs = result.get("messages") or []
        ai_msgs = [m for m in msgs if isinstance(m, AIMessage)]
        ai_response = ai_msgs[-1].content if ai_msgs else "I'm processing your request..."

        # 6) Persist AI message
        ai_msg = DBMessage(
            session_id=session_row.id,
            sender=Sender.agent.value,
            role=Role.assistant.value,
            content=ai_response,
            meta_json={},
        )
        db.add(ai_msg)

        # 7) Upsert hiring context from result (if any)
        updated_hiring = result.get("hiring_data") or {}
        ctx = _upsert_hiring_context(db, session_row.id, updated_hiring)

        # 8) Validate & update current_step
        new_step_raw = result.get("current_step") or session_row.current_step
        try:
            session_row.current_step = StepName(new_step_raw).value  # normalize to enum value
        except ValueError:
            # keep prior step if agent returned an unknown one
            pass

        db.commit()
        log.info("Chat response generated", extra={"Chat response" : response, "type": type(response)})
        response = ChatResponse(
            session_id=session_row.id,
            response=ai_response,
            current_step=StepName(session_row.current_step),
            hiring_context=_context_to_hiring_dict(ctx),
        )

        return response

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")