from typing import cast

import discord
from discord import app_commands
from discord.ext import commands

from utils.ids import Meta, Role


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @commands.hybrid_command(name="ping", description="Test the bot's latency.")
    @app_commands.guilds(Meta.SERVER.value)
    async def ping(self, ctx: commands.Context[commands.Bot]):
        latency = round(self.bot.latency * 1000)
        await ctx.reply(content=f"🏓 pong! took {latency}ms", ephemeral=True)

    @commands.hybrid_command(
        name="snowpea", description="React to the past 'n' messages with snowpea."
    )
    @app_commands.guilds(Meta.SERVER.value)
    @app_commands.guild_only()
    async def snowpea(self, ctx: commands.Context[commands.Bot], n: int = 1):
        guild = cast(discord.Guild, self.bot.get_guild(Meta.SERVER.value))
        channel = cast(
            discord.TextChannel, guild.get_channel(Meta.CURRENT_STUDENT_CHANNEL.value)
        )

        if ctx.channel == channel:
            return await ctx.reply(
                content="why would you use this command in the current student channel",
                ephemeral=True,
            )

        mentioned_users: set[str] = set()
        async for message in ctx.channel.history(limit=n):
            if not message.author:
                continue

            member = message.author
            if isinstance(member, discord.User):
                try:
                    member = await guild.fetch_member(member.id)
                except discord.NotFound:
                    continue

            if any(role.id == Role.PROSPECTIVE_STUDENT.value for role in member.roles):
                continue

            await message.add_reaction(
                discord.PartialEmoji(name="snowpea", id=Meta.SNOWPEA.value)
            )

            mentioned_users.add(message.author.mention)

        if mentioned_users:
            mention_text = ", ".join(mentioned_users)
            await channel.send(f"{mention_text} please resume your conversation here")

        await ctx.reply(content="done", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
