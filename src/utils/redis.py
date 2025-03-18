# pyright: reportUnknownMemberType=false
# pyright: reportDeprecated=false

import os
from collections.abc import Awaitable
from typing import Set, cast

import redis.asyncio as redis


class RedisManager:
    def __init__(self, key_prefix: str) -> None:
        # check if running locally and use the appropriate Redis URL
        is_local = os.getenv("ENVIRONMENT") == "local"
        if is_local:
            self.redis_url: str = cast(str, os.getenv("REDIS_URL_LOCAL"))
        else:
            self.redis_url = cast(str, os.getenv("REDIS_URL"))

        self.redis: redis.Redis | None = None

        self.key_prefix: str = key_prefix
        self.set_key: str = f"all_{key_prefix}"

    def get_key(self, key: str) -> str:
        return f"{self.key_prefix}:{key}"

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

    async def get(self, key: str) -> str | None:
        if not self.redis:
            raise redis.ConnectionError("Redis client not initialized")

        prefixed_key = self.get_key(key)
        return await cast(Awaitable[str | None], self.redis.get(prefixed_key))

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        if not self.redis:
            raise redis.ConnectionError("Redis client not initialized")

        prefixed_key = self.get_key(key)
        return await cast(Awaitable[bool], self.redis.set(prefixed_key, value, ex=ex))

    async def delete(self, key: str) -> int:
        if not self.redis:
            raise redis.ConnectionError("Redis client not initialized")

        prefixed_key = self.get_key(key)
        return await cast(Awaitable[int], self.redis.delete(prefixed_key))

    async def exists(self, key: str) -> bool:
        if not self.redis:
            raise redis.ConnectionError("Redis client not initialized")

        prefixed_key = self.get_key(key)
        result = await cast(Awaitable[int], self.redis.exists(prefixed_key))
        return bool(result)

    # set operations
    async def sadd(self, value: str) -> int:
        if not self.redis:
            raise redis.ConnectionError("Redis client not initialized")

        return await cast(Awaitable[int], self.redis.sadd(self.set_key, value))

    async def sismember(self, value: str) -> bool:
        if not self.redis:
            raise redis.ConnectionError("Redis client not initialized")

        result = await cast(Awaitable[int], self.redis.sismember(self.set_key, value))
        return bool(result)

    async def smembers(self) -> Set[str]:
        if not self.redis:
            raise redis.ConnectionError("Redis client not initialized")

        return await cast(Awaitable[set[str]], self.redis.smembers(self.set_key))

    async def srem(self, value: str) -> int:
        if not self.redis:
            raise redis.ConnectionError("Redis client not initialized")

        return await cast(Awaitable[int], self.redis.srem(self.set_key, value))
