import asyncio
import io
import random
import re
import sys
import textwrap
import traceback
import typing
from typing import override

import discord
import requests
from discord import TextChannel, Thread, app_commands
from discord.abc import GuildChannel, PrivateChannel
from discord.ext import commands

from utils.ids import Meta, Role, eval_whitelist


class RedirectToEmbed(io.StringIO):
    def __init__(self, ctx: commands.Context[commands.Bot]):
        super().__init__()
        self.ctx: commands.Context[commands.Bot] = ctx
        self.output: list[str] = []

    @override
    def write(self, message: str):
        if message.strip():
            self.output.append(message)

        return len(message)


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self._eval_messages: dict[
            int, tuple[commands.Context[commands.Bot], discord.Message]
        ] = {}

    @commands.hybrid_command(name="ping", description="Test the bot's latency.")
    @app_commands.guilds(Meta.SERVER.value)
    async def ping(self, ctx: commands.Context[commands.Bot]):
        latency = round(self.bot.latency * 1000)
        await ctx.reply(content=f"🏓 pong! took {latency}ms", ephemeral=True)

    @commands.command(name="echo", hidden=True)
    @commands.is_owner()
    async def echo(self, ctx: commands.Context[commands.Bot], *, message: str):
        await ctx.message.delete()
        await ctx.send(content=message)

    async def _eval_helper(self, ctx: commands.Context[commands.Bot], code: str):
        from utils.redis import RedisManager

        # create RedisManager just for connection, but use raw client for arbitrary keys
        # the prefix doesn't matter, we won't use the wrapper methods
        redis_manager = RedisManager(key_prefix="temp")
        await redis_manager.connect()

        async def get_member(id: int) -> discord.Member | None:
            return await ctx.guild.fetch_member(id) if ctx.guild else None

        async def get_user(id: int) -> discord.User | None:
            return await self.bot.fetch_user(id)

        async def get_channel(id: int) -> GuildChannel | PrivateChannel | Thread:
            return await self.bot.fetch_channel(id)

        async def get_guild(id: int) -> discord.Guild | None:
            return await self.bot.fetch_guild(id)

        async def get_message(
            channel_id: int, message_id: int
        ) -> discord.Message | None:
            channel = await get_channel(channel_id)
            if isinstance(channel, (TextChannel, Thread)):
                return await channel.fetch_message(message_id)

            return None

        env: dict[str, typing.Any] = {
            "__builtins__": __builtins__,
            "bot": self.bot,
            "ctx": ctx,
            "redis": redis_manager.redis,
            "discord": discord,
            "commands": commands,
            "random": random,
            "requests": requests,
            "asyncio": asyncio,
            "get_member": get_member,
            "get_user": get_user,
            "get_channel": get_channel,
            "get_guild": get_guild,
            "get_message": get_message,
            "Meta": Meta,
            "Role": Role,
        }

        original_stdout = sys.stdout
        stdout_output = ""
        sys.stdout = RedirectToEmbed(ctx)

        code = re.sub(r"```(?:py|python)?\n([\s\S]+?)\n```", r"\1", code)
        code = re.sub(r"^`([^`]+)`$", r"\1", code)
        lines = code.splitlines()

        try:
            body = textwrap.indent("\n".join(lines[:-1]), "    ")
            code = textwrap.dedent(
                f"async def __eval():\n{body}\n    return {lines[-1]}"
            )

            exec(compile(code, "<eval>", "exec"), env)
            result = await env["__eval"]()

            embed = discord.Embed(color=discord.Color.green())
            embed.add_field(name="result", value=f"```py\n{result}\n```", inline=False)
        except Exception as e:
            error = "".join(traceback.format_exception(type(e), e, e.__traceback__))

            embed = discord.Embed(color=discord.Color.red())
            embed.add_field(name="stderr", value=f"```py\n{error}\n```", inline=False)
        finally:
            stdout_output = "\n".join(sys.stdout.output)
            sys.stdout = original_stdout

            # clean up the redis connection
            try:
                await redis_manager.close()
            except Exception as e:
                print(f"Failed to close redis connection: {e}")
                pass

        if stdout_output:
            embed.add_field(
                name="stdout", value=f"```py\n{stdout_output}\n```", inline=False
            )

        return embed

    @commands.command(name="eval", hidden=True)
    @eval_whitelist
    async def eval_cmd(self, ctx: commands.Context[commands.Bot], *, code: str):
        embed = await self._eval_helper(ctx, code)
        response = await ctx.reply(embed=embed)

        self._eval_messages[ctx.message.id] = (ctx, response)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.id not in self._eval_messages:
            return
        if after.content == before.content:
            return

        # try to get a fresh context from the edited message
        ctx = await self.bot.get_context(after)
        if ctx.command is None or ctx.command.name != "eval":
            return  # it's no longer an eval command

        # manually call the command again with the edited message
        self._eval_messages[after.id] = (ctx, self._eval_messages[after.id][1])
        await self.bot.invoke(ctx)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
