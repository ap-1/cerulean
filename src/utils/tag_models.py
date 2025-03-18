import datetime
import json
from dataclasses import dataclass

from utils.ids import Meta


def get_int(value: object, default: int = 0) -> int:
    return int(value) if isinstance(value, (int, str)) else default


@dataclass
class TagData:
    name: str
    content: str
    author_id: int
    author_name: str  # backup in case author leaves server
    created_at: datetime.datetime
    starred: bool = False
    uses: int = 0
    message_id: int = 0
    channel_id: int = 0

    @property
    def message_link(self) -> str | None:
        if self.message_id and self.channel_id:
            return f"https://discord.com/channels/{Meta.SERVER.value}/{self.channel_id}/{self.message_id}"
        return None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "TagData":
        return cls(
            name=str(data["name"]),
            content=str(data["content"]),
            author_id=get_int(data["author_id"]),
            author_name=str(data["author_name"]),
            created_at=datetime.datetime.fromisoformat(str(data["created_at"])),
            starred=bool(data.get("starred", False)),
            uses=get_int(data["uses"]),
            message_id=get_int(data["message_id"]),
            channel_id=get_int(data["channel_id"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "content": self.content,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "created_at": self.created_at.isoformat(),
            "starred": self.starred,
            "uses": self.uses,
            "message_id": self.message_id,
            "channel_id": self.channel_id,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
