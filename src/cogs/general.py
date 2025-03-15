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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
