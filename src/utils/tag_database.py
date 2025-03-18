# pyright: reportUnknownMemberType=false

import json
from typing import TYPE_CHECKING

from utils.redis import RedisManager

if TYPE_CHECKING:
    from utils.tag_models import TagData


class TagDatabase(RedisManager):
    def __init__(self) -> None:
        super().__init__(key_prefix="tag")

    async def get_all_tags(self) -> dict[str, "TagData"]:
        from utils.tag_models import TagData

        tags: dict[str, TagData] = {}
        tag_names = await self.smembers("")

        # get each tag's data
        for name in tag_names:
            tag_json = await self.get(name)
            if tag_json:
                tag_dict = json.loads(tag_json)
                tags[name] = TagData.from_dict(tag_dict)

        return tags

    async def get_tag(self, name: str) -> "TagData | None":
        from utils.tag_models import TagData

        tag_json = await self.get(name)
        if tag_json:
            tag_dict = json.loads(tag_json)
            return TagData.from_dict(tag_dict)

        return None

    async def add_tag(self, tag: "TagData") -> bool:
        # add the tag name to the set of all tags
        await self.sadd("", tag.name)

        return await self.set(tag.name, tag.to_json())

    async def update_tag(self, tag: "TagData") -> bool:
        exists = await self.exists(tag.name)
        if not exists:
            return False

        # update the tag data
        return await self.set(tag.name, tag.to_json())

    async def delete_tag(self, name: str) -> bool:
        exists = await self.exists(name)
        if not exists:
            return False

        # remove the tag name from the set of all tags
        await self.srem("", name)

        await self.delete(name)
        return True
