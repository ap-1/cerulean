from typing import cast

import discord
from discord import app_commands
from discord.ext import commands

from utils.ids import Meta, Role
from views.student_type import NameModal


class Verify(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.verification_sessions: dict[int, str] = {}

    @app_commands.command(
        name="verify", description="Verify yourself to get access to the server."
    )
    @app_commands.guilds(Meta.SERVER.value)
    @app_commands.guild_only()
    async def verify(self, interaction: discord.Interaction):
        guild = cast(discord.Guild, self.bot.get_guild(Meta.SERVER.value))
        member = guild.get_member(interaction.user.id)
        if not member:
            await interaction.response.send_message(
                content="oops! please join the server and try again.",
                ephemeral=True,
            )
            return

        unverified = cast(discord.Role, guild.get_role(Role.UNVERIFIED.value))
        if unverified not in member.roles:
            await interaction.response.send_message(
                content="oops! you're already verified!",
                ephemeral=True,
            )
            return

        channel = cast(
            discord.TextChannel, guild.get_channel(Meta.VERIFY_CHANNEL.value)
        )
        if interaction.channel_id != channel.id:
            await interaction.response.send_message(
                content="oops! please use the verification channel.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(NameModal())


async def setup(bot: commands.Bot):
    await bot.add_cog(Verify(bot))
