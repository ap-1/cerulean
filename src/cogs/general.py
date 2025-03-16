import re
import textwrap
import traceback
import typing

import discord
from discord import app_commands
from discord.ext import commands

from utils.ids import Meta


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @commands.hybrid_command(name="ping", description="Test the bot's latency.")
    @app_commands.guilds(Meta.SERVER.value)
    async def ping(self, ctx: commands.Context[commands.Bot]):
        latency = round(self.bot.latency * 1000)
        await ctx.reply(content=f"🏓 pong! took {latency}ms", ephemeral=True)

    @commands.command(name="eval", hidden=True)
    @commands.is_owner()
    async def eval_cmd(self, ctx: commands.Context[commands.Bot], *, code: str):
        env: dict[str, typing.Any] = {
            "__builtins__": __builtins__,
            "bot": self.bot,
            "ctx": ctx,
            "discord": discord,
            "commands": commands,
        }

        code = re.sub(r"```(?:py|python)?\n([\s\S]+?)\n```", r"\1", code)
        code = re.sub(r"^`([^`]+)`$", r"\1", code)

        try:
            code = textwrap.dedent(
                f"async def __eval():\n{textwrap.indent(code, '    ')}\n    return {code}"
            )

            exec(compile(code, "<eval>", "exec"), env)
            result = await env["__eval"]()

            embed = discord.Embed(
                description=f"```py\n{result}\n```",
                color=discord.Color.green(),
            )

        except Exception as e:
            error = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            embed = discord.Embed(
                description=f"```py\n{error}\n```",
                color=discord.Color.red(),
            )

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
