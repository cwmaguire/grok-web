from enum import Enum
from pydantic import BaseModel


class EventType(str, Enum):
    TEXT_DELTA = "text_delta"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TURN_START = "turn_start"
    DONE = "done"
    CANCELLED = "cancelled"
    ERROR = "error"


class StreamEvent(BaseModel):
    type: EventType
    data: dict | None = None

    def to_ws(self) -> dict:
        msg = {"type": self.type.value}
        if self.data is not None:
            msg["data"] = self.data
        return msg


class ConversationCreate(BaseModel):
    title: str = "New Conversation"


class ConversationUpdate(BaseModel):
    title: str


class UserMessage(BaseModel):
    type: str = "user_message"
    content: str
