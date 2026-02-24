from fastapi import APIRouter, HTTPException

from grok_web.models import ConversationCreate, ConversationUpdate
from grok_web.db import Database

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def get_db() -> Database:
    from grok_web.main import app_state
    return app_state["db"]


@router.post("")
async def create_conversation(body: ConversationCreate):
    db = get_db()
    return await db.create_conversation(body.title)


@router.get("")
async def list_conversations():
    db = get_db()
    return await db.list_conversations()


@router.get("/{conv_id}")
async def get_conversation(conv_id: str):
    db = get_db()
    conv = await db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.patch("/{conv_id}")
async def update_conversation(conv_id: str, body: ConversationUpdate):
    db = get_db()
    conv = await db.update_conversation(conv_id, body.title)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/{conv_id}")
async def delete_conversation(conv_id: str):
    db = get_db()
    conv = await db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete_conversation(conv_id)
    return {"ok": True}


@router.get("/{conv_id}/messages")
async def get_messages(conv_id: str):
    db = get_db()
    conv = await db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return await db.get_messages(conv_id)
