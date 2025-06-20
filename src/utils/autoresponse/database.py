import json

from utils.redis import RedisManager
from utils.autoresponse.models import AutoresponseData


class AutoresponseDatabase(RedisManager):
    def __init__(self) -> None:
        super().__init__(key_prefix="autoresponse")

    async def get_all_autoresponses(self) -> dict[str, AutoresponseData]:
        autoresponses: dict[str, AutoresponseData] = {}
        names = await self.smembers("")

        for name in names:
            data_json = await self.get(name)
            if data_json:
                data_dict = json.loads(data_json)
                autoresponses[name] = AutoresponseData.from_dict(data_dict)

        return autoresponses

    async def get_autoresponse(self, name: str) -> AutoresponseData | None:
        data_json = await self.get(name)
        if data_json:
            data_dict = json.loads(data_json)
            return AutoresponseData.from_dict(data_dict)

        return None

    async def add_autoresponse(self, autoresponse: AutoresponseData) -> bool:
        await self.sadd("", autoresponse.name)
        return await self.set(autoresponse.name, autoresponse.to_json())

    async def update_autoresponse(self, autoresponse: AutoresponseData) -> bool:
        exists = await self.exists(autoresponse.name)
        if not exists:
            return False

        return await self.set(autoresponse.name, autoresponse.to_json())

    async def delete_autoresponse(self, name: str) -> bool:
        exists = await self.exists(name)
        if not exists:
            return False

        await self.srem("", name)
        await self.delete(name)
        return True
