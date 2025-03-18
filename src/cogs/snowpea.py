import time
from typing import cast, override

import discord
from discord import PartialEmoji
from discord.ext import commands

from utils.ids import Meta, Role
from utils.redis import RedisManager

SNOWPEA_COOLDOWN_SECONDS = 30


class SnowpeaTracker(RedisManager):
    def __init__(self) -> None:
        super().__init__(key_prefix="snowpea")

    async def is_message_processed(self, message_id: int) -> bool:
        try:
            return await self.sismember(str(message_id))
        except Exception:
            # assume not processed if Redis error occurs
            return False

    async def mark_message_processed(self, message_id: int) -> None:
        await self.sadd(str(message_id))

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


class Snowpea(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.tracker: SnowpeaTracker = SnowpeaTracker()

        self.bot.loop.create_task(self.tracker.connect())

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # ignore own reactions
        if (
            not self.bot.user
            or not payload.member
            or payload.user_id == self.bot.user.id
        ):
            return

        # ignore non-snowpea reactions
        if payload.emoji.name != "snowpea" or payload.emoji.id != Meta.SNOWPEA.value:
            return

        # ignore reactions in the wrong server
        if not payload.guild_id or payload.guild_id != Meta.SERVER.value:
            return

        # ignore if reaction not made by an admin/mod
        member = payload.member
        if not any(
            role.id in (Role.ADMIN.value, Role.MOD.value) for role in member.roles
        ):
            return

        guild = cast(discord.Guild, self.bot.get_guild(payload.guild_id))
        channel = cast(discord.TextChannel, guild.get_channel(payload.channel_id))
        message = await channel.fetch_message(payload.message_id)

        def remove_reaction():
            return message.remove_reaction(
                discord.PartialEmoji(name="snowpea", id=Meta.SNOWPEA.value),
                member,
            )

        # decline if reaction is in the current student channel
        if channel.id == Meta.CURRENT_STUDENT_CHANNEL.value:
            return await remove_reaction()

        # decline if author is a prospective student or a bot
        author = cast(discord.Member, message.author)
        if author.bot or any(
            role.id == Role.PROSPECTIVE_STUDENT.value for role in author.roles
        ):
            return await remove_reaction()

        # check if this message has already been processed
        if await self.tracker.is_message_processed(payload.message_id):
            return await remove_reaction()

        # mark the message as processed to prevent duplicates
        await self.tracker.mark_message_processed(payload.message_id)

        # replace reaction with own reaction
        await message.clear_reaction(
            emoji=PartialEmoji(name="snowpea", id=Meta.SNOWPEA.value)
        )
        await message.add_reaction(
            discord.PartialEmoji(name="snowpea", id=Meta.SNOWPEA.value)
        )

        # don't ping if author is in cooldown period
        if await self.tracker.is_author_in_cooldown(author.id):
            return

        await self.tracker.set_author_cooldown(author.id)

        current_student_channel = cast(
            discord.TextChannel, guild.get_channel(Meta.CURRENT_STUDENT_CHANNEL.value)
        )
        await current_student_channel.send(
            f"{author.mention}, {member.display_name} wants you to resume your conversation {message.jump_url} here"
        )

    @override
    async def cog_unload(self) -> None:
        try:
            await self.tracker.close()
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Snowpea(bot))
