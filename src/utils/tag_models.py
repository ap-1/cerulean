import datetime
import json
from dataclasses import dataclass


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

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "TagData":
        """Create a TagData instance from a dictionary."""
        return cls(
            name=str(data["name"]),
            content=str(data["content"]),
            author_id=get_int(data["author_id"]),
            author_name=str(data["author_name"]),
            created_at=datetime.datetime.fromisoformat(str(data["created_at"])),
            starred=bool(data.get("starred", False)),
            uses=get_int(data["uses"]),
        )

    def to_dict(self) -> dict[str, object]:
        """Convert this TagData instance to a dictionary."""
        return {
            "name": self.name,
            "content": self.content,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "created_at": self.created_at.isoformat(),
            "starred": self.starred,
            "uses": self.uses,
        }

    def to_json(self) -> str:
        """Convert to JSON string for Redis storage."""
        return json.dumps(self.to_dict())
