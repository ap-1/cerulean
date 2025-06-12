from typing import override

import discord
from discord import app_commands
from discord.ext import commands

from utils.ids import Meta, is_whitelisted
from utils.redis import RedisManager


class Nickname(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.redis_manager: RedisManager = RedisManager(key_prefix="nickname")

        self.bot.loop.create_task(self._init_redis())

    async def _init_redis(self) -> None:
        try:
            await self.redis_manager.connect()
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            raise

    @override
    async def cog_unload(self) -> None:
        try:
            await self.redis_manager.close()
        except Exception:
            pass

    @commands.hybrid_command(name="nick", description="Enforce a nickname for a user.")
    @app_commands.guilds(Meta.SERVER.value)
    @app_commands.describe(
        user="The user to set a nickname for",
        nickname="The nickname to set (leave empty to remove saved nickname)",
    )
    @is_whitelisted
    async def nick(
        self,
        ctx: commands.Context[commands.Bot],
        user: discord.Member,
        *,
        nickname: str | None = None,
    ) -> None:
        if not ctx.guild or ctx.guild.id != Meta.SERVER.value:
            await ctx.reply(
                "this command can only be used in the server", ephemeral=True
            )
            return

        user_id = str(user.id)

        if nickname is None:
            # remove saved nickname
            deleted = await self.redis_manager.delete(user_id)
            if deleted:
                await ctx.reply(
                    f"removed saved nickname for {user.mention}", ephemeral=True
                )
            else:
                await ctx.reply(
                    f"no saved nickname found for {user.mention}", ephemeral=True
                )
        else:
            if len(nickname) > 32:
                await ctx.reply(
                    "nickname cannot be longer than 32 characters", ephemeral=True
                )
                return

            await self.redis_manager.set(user_id, nickname)

            # try to set the nickname immediately
            try:
                await user.edit(nick=nickname)
                await ctx.reply(
                    f"saved nickname `{nickname}` for {user.mention}", ephemeral=True
                )
            except (discord.Forbidden, discord.HTTPException):
                await ctx.reply(
                    f"saved nickname `{nickname}` for {user.mention}, but couldn't set it",
                    ephemeral=True,
                )

    @commands.Cog.listener()
    async def on_member_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        # if in the target server
        if after.guild.id != Meta.SERVER.value:
            return

        # if nickname changed
        if before.nick == after.nick:
            return

        user_id = str(after.id)
        try:
            saved_nickname = await self.redis_manager.get(user_id)
        except Exception as e:
            print(f"Failed to fetch saved nickname for {after.id}: {e}")
            return

        if saved_nickname is None:
            return

        if after.nick == saved_nickname:
            return

        # set the saved nickname
        try:
            await after.edit(nick=saved_nickname)
        except (discord.Forbidden, discord.HTTPException):
            print(f"Failed to set saved nickname for {after.display_name} ({after.id})")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Nickname(bot))
