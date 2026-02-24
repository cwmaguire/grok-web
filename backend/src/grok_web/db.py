import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT,
    tool_calls TEXT,
    tool_use_id TEXT,
    is_error INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    seq INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, seq);
"""


class Database:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self):
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # --- Conversations ---

    async def create_conversation(self, title: str = "New Conversation") -> dict:
        conv_id = str(uuid.uuid4())
        now = self._now()
        await self._db.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conv_id, title, now, now),
        )
        await self._db.commit()
        return {"id": conv_id, "title": title, "created_at": now, "updated_at": now}

    async def list_conversations(self) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_conversation(self, conv_id: str) -> dict | None:
        cursor = await self._db.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def update_conversation(self, conv_id: str, title: str) -> dict | None:
        now = self._now()
        await self._db.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, now, conv_id),
        )
        await self._db.commit()
        return await self.get_conversation(conv_id)

    async def delete_conversation(self, conv_id: str):
        await self._db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        await self._db.commit()

    async def touch_conversation(self, conv_id: str):
        now = self._now()
        await self._db.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conv_id)
        )
        await self._db.commit()

    # --- Messages ---

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str | None = None,
        tool_calls: list | None = None,
        tool_use_id: str | None = None,
        is_error: bool = False,
    ) -> dict:
        msg_id = str(uuid.uuid4())
        now = self._now()

        cursor = await self._db.execute(
            "SELECT COALESCE(MAX(seq), 0) FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        )
        row = await cursor.fetchone()
        seq = row[0] + 1

        tool_calls_json = json.dumps(tool_calls) if tool_calls else None

        await self._db.execute(
            """INSERT INTO messages (id, conversation_id, role, content, tool_calls, tool_use_id, is_error, created_at, seq)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (msg_id, conversation_id, role, content, tool_calls_json, tool_use_id, int(is_error), now, seq),
        )
        await self._db.commit()
        await self.touch_conversation(conversation_id)

        return {
            "id": msg_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "tool_calls": tool_calls,
            "tool_use_id": tool_use_id,
            "is_error": is_error,
            "created_at": now,
            "seq": seq,
        }

    async def get_messages(self, conversation_id: str) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY seq",
            (conversation_id,),
        )
        rows = await cursor.fetchall()
        messages = []
        for r in rows:
            msg = dict(r)
            if msg["tool_calls"]:
                msg["tool_calls"] = json.loads(msg["tool_calls"])
            msg["is_error"] = bool(msg["is_error"])
            messages.append(msg)
        return messages
