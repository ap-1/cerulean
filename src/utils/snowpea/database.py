import time

from utils.redis import RedisManager

SNOWPEA_COOLDOWN_SECONDS = 30


class SnowpeaDatabase(RedisManager):
    def __init__(self) -> None:
        super().__init__(key_prefix="snowpea")

    async def is_message_processed(self, message_id: int) -> bool:
        try:
            return await self.sismember("", str(message_id))
        except Exception:
            # assume not processed if Redis error occurs
            return False

    async def mark_message_processed(self, message_id: int) -> None:
        await self.sadd("", str(message_id))

    async def set_author_cooldown(self, author_id: int) -> None:
        cooldown_key = f"cooldown:{author_id}"
        current_time = int(time.time())
        await self.set(cooldown_key, str(current_time))

    async def is_author_in_cooldown(self, author_id: int) -> bool:
        cooldown_key = f"cooldown:{author_id}"
        try:
            last_snowpea_time = await self.get(cooldown_key)
            if last_snowpea_time:
                current_time = int(time.time())
                elapsed_time = current_time - int(last_snowpea_time)

                return elapsed_time < SNOWPEA_COOLDOWN_SECONDS
        except Exception:
            # assume not in cooldown if Redis error occurs
            pass
        return False

    async def increment_received_count(self, user_id: int) -> int:
        key = f"received:{user_id}"
        current_count = await self.get(key)
        count = 1

        if current_count:
            try:
                count = int(current_count) + 1
            except ValueError:
                count = 1

        # update the count
        await self.set(key, str(count))
        await self.sadd("received_users", str(user_id))

        return count

    async def increment_initiated_count(self, user_id: int) -> int:
        key = f"initiated:{user_id}"
        current_count = await self.get(key)
        count = 1

        if current_count:
            try:
                count = int(current_count) + 1
            except ValueError:
                count = 1

        # update the count
        await self.set(key, str(count))
        await self.sadd("initiated_users", str(user_id))

        return count

    async def get_received_count(self, user_id: int) -> int:
        key = f"received:{user_id}"
        count = await self.get(key)

        if count:
            try:
                return int(count)
            except ValueError:
                return 0
        return 0

    async def get_initiated_count(self, user_id: int) -> int:
        key = f"initiated:{user_id}"
        count = await self.get(key)

        if count:
            try:
                return int(count)
            except ValueError:
                return 0
        return 0

    async def get_users_with_stats(self, stat_type: str) -> set[str]:
        if stat_type.lower() == "received":
            return await self.smembers("received_users")
        elif stat_type.lower() == "initiated":
            return await self.smembers("initiated_users")

        return set()
