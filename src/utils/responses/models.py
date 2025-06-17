import json
from dataclasses import dataclass


def get_float(value: object, default: float = 1.0) -> float:
    return float(value) if isinstance(value, (float, str)) else default


@dataclass
class AutoresponseData:
    name: str
    triggers: list[str]
    template: str
    probability: float = 1.0

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "AutoresponseData":
        return cls(
            name=str(data["name"]),
            probability=get_float(data["probability"]),
            triggers=[
                str(t)  # pyright: ignore[reportUnknownArgumentType]
                for t in data.get(  # pyright: ignore[reportUnknownVariableType, reportGeneralTypeIssues]
                    "triggers", []
                )  # ty: ignore[not-iterable]
            ],
            template=str(data["template"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "probability": self.probability,
            "triggers": self.triggers,
            "template": self.template,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
