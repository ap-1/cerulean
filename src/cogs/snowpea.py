from typing import cast

import discord
from discord import app_commands
from discord.ext import commands

from utils.ids import Meta, Role


async def not_current_student_channel(interaction: discord.Interaction) -> bool:
    # decline if reaction is in the current student channel
    if interaction.channel_id == Meta.CURRENT_STUDENT_CHANNEL.value:
        await interaction.response.send_message(
            "why would you snowpea in the current student channel",
            ephemeral=True,
        )
        return False

    return True


class Snowpea(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.context_menu()
    @app_commands.guilds(Meta.SERVER.value)
    @app_commands.check(not_current_student_channel)
    async def snowpea(self, interaction: discord.Interaction, message: discord.Message):
        guild = cast(discord.Guild, self.bot.get_guild(Meta.SERVER.value))
        channel = cast(
            discord.TextChannel, guild.get_channel(Meta.CURRENT_STUDENT_CHANNEL.value)
        )

        if not message.author:
            return await interaction.response.send_message(
                "message has no author", ephemeral=True
            )

        member = message.author
        if isinstance(member, discord.User):
            try:
                member = await guild.fetch_member(member.id)
            except discord.NotFound:
                return await interaction.response.send_message(
                    "user is not in the server", ephemeral=True
                )

        # decline if member is a prospective student
        if any(role.id == Role.PROSPECTIVE_STUDENT.value for role in member.roles):
            return await interaction.response.send_message(
                "why would you snowpea a prospective student",
                ephemeral=True,
            )

        await message.add_reaction(
            discord.PartialEmoji(name="snowpea", id=Meta.SNOWPEA.value)
        )

        await channel.send(f"{member.mention} please resume your conversation here")
        await interaction.response.send_message("done!", ephemeral=True)

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

        guild = cast(discord.Guild, self.bot.get_guild(payload.guild_id))
        channel = cast(discord.TextChannel, guild.get_channel(payload.channel_id))

        # decline if reaction is in the current student channel
        if channel.id == Meta.CURRENT_STUDENT_CHANNEL.value:
            return await channel.send(
                f"{payload.member.mention} why would you snowpea in the current student channel"
            )

        current_student_channel = cast(
            discord.TextChannel, guild.get_channel(Meta.CURRENT_STUDENT_CHANNEL.value)
        )
        message = await channel.fetch_message(payload.message_id)
        member = cast(discord.Member, message.author)

        # decline if member is a prospective student
        if any(role.id == Role.PROSPECTIVE_STUDENT.value for role in member.roles):
            return await channel.send(
                f"{payload.member.mention} why would you snowpea a prospective student"
            )

        await current_student_channel.send(
            f"{member.mention} please resume your conversation here"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Snowpea(bot))
