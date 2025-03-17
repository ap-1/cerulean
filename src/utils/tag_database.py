# pyright: reportUnknownMemberType=false

import json
import os
from collections.abc import Awaitable
from typing import TYPE_CHECKING, cast

import redis.asyncio as redis

if TYPE_CHECKING:
    from utils.tag_models import TagData


class TagDatabase:
    def __init__(self) -> None:
        # check if running locally and use the appropriate Redis URL
        is_local = os.getenv("ENVIRONMENT") == "local"
        if is_local:
            self.redis_url: str = cast(str, os.getenv("REDIS_URL_LOCAL"))
        else:
            self.redis_url = cast(str, os.getenv("REDIS_URL"))

        self.redis: redis.Redis | None = None
        self.key_prefix: str = "tag:"
        self.tags_set_key: str = "all_tags"

    async def connect(self) -> None:
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)

            # test connection
            if self.redis:
                await self.redis.ping()
                print(f"Successfully connected to Redis at {self.redis_url}")
            else:
                raise redis.ConnectionError("Failed to initialize Redis client")
        except redis.ConnectionError as e:
            print(f"Failed to connect to Redis at {self.redis_url}: {e}")
            raise

    async def close(self) -> None:
        if self.redis:
            await self.redis.close()
            print("Redis connection closed")

    async def get_all_tags(self) -> dict[str, "TagData"]:
        from utils.tag_models import TagData

        tags: dict[str, TagData] = {}
        try:
            if not self.redis:
                raise redis.ConnectionError("Redis client not initialized")

            tag_names: set[str] = await cast(
                Awaitable[set[str]], self.redis.smembers(self.tags_set_key)
            )

            # get each tag's data
            for name in tag_names:
                tag_json = await self.redis.get(f"{self.key_prefix}{name}")
                if tag_json:
                    tag_dict = json.loads(tag_json)
                    tags[name] = TagData.from_dict(tag_dict)
        except Exception as e:
            print(f"Error getting all tags: {e}")
            raise

        return tags

    async def get_tag(self, name: str) -> "TagData | None":
        from utils.tag_models import TagData

        try:
            if not self.redis:
                raise redis.ConnectionError("Redis client not initialized")

            tag_json = await self.redis.get(f"{self.key_prefix}{name}")
            if tag_json:
                tag_dict = json.loads(tag_json)
                return TagData.from_dict(tag_dict)
        except Exception as e:
            print(f"Error getting tag {name}: {e}")
            raise

        return None

    async def add_tag(self, tag: "TagData") -> bool:
        try:
            if not self.redis:
                raise redis.ConnectionError("Redis client not initialized")

            await self.redis.set(f"{self.key_prefix}{tag.name}", tag.to_json())

            # add the tag name to the set of all tags
            await cast(Awaitable[int], self.redis.sadd(self.tags_set_key, tag.name))

            return True
        except Exception as e:
            print(f"Error adding tag {tag.name}: {e}")
            raise

    async def update_tag(self, tag: "TagData") -> bool:
        try:
            if not self.redis:
                raise redis.ConnectionError("Redis client not initialized")

            exists = await cast(
                Awaitable[int], self.redis.exists(f"{self.key_prefix}{tag.name}")
            )
            if not exists:
                return False

            # update the tag data
            await cast(
                Awaitable[bool],
                self.redis.set(f"{self.key_prefix}{tag.name}", tag.to_json()),
            )

            return True
        except Exception as e:
            print(f"Error updating tag {tag.name}: {e}")
            raise

    async def delete_tag(self, name: str) -> bool:
        try:
            if not self.redis:
                raise redis.ConnectionError("Redis client not initialized")

            exists = await self.redis.exists(f"{self.key_prefix}{name}")
            if not exists:
                return False

            await self.redis.delete(f"{self.key_prefix}{name}")

            # remove the tag name from the set of all tags
            await cast(Awaitable[int], self.redis.srem(self.tags_set_key, name))

            return True
        except Exception as e:
            print(f"Error deleting tag {name}: {e}")
            raise
