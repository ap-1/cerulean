from typing import cast, override

import discord
from discord import PartialEmoji, app_commands
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

        self.snowpea_context: app_commands.ContextMenu = app_commands.ContextMenu(
            name="snowpea",
            callback=self.snowpea_callback,
            guild_ids=[Meta.SERVER.value],
        )
        self.snowpea_context.add_check(not_current_student_channel)
        self.bot.tree.add_command(self.snowpea_context)

    async def snowpea_callback(
        self, interaction: discord.Interaction, message: discord.Message
    ):
        guild = cast(discord.Guild, self.bot.get_guild(Meta.SERVER.value))
        channel = cast(
            discord.TextChannel, guild.get_channel(Meta.CURRENT_STUDENT_CHANNEL.value)
        )

        if not message.author:
            return await interaction.response.send_message(
                "message has no author", ephemeral=True
            )

        author = message.author
        if isinstance(author, discord.User):
            try:
                author = await guild.fetch_member(author.id)
            except discord.NotFound:
                return await interaction.response.send_message(
                    "user is not in the server", ephemeral=True
                )

        # ignore if anyone has already reacted to this message
        if any(
            reaction.count > 1
            and isinstance(reaction.emoji, discord.PartialEmoji)
            and reaction.emoji.id == Meta.SNOWPEA.value
            for reaction in message.reactions
        ):
            return await interaction.response.send_message(
                "someone has already snowpea'd this message", ephemeral=True
            )

        # decline if member is a prospective student
        if any(role.id == Role.PROSPECTIVE_STUDENT.value for role in author.roles):
            return await interaction.response.send_message(
                "user is a prospective student",
                ephemeral=True,
            )

        await message.add_reaction(
            discord.PartialEmoji(name="snowpea", id=Meta.SNOWPEA.value)
        )

        await channel.send(
            f"{author.mention} please resume your conversation {message.jump_url} here"
        )
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

        member = payload.member

        def remove_reaction():
            return message.remove_reaction(
                discord.PartialEmoji(name="snowpea", id=Meta.SNOWPEA.value),
                member,
            )

        # decline if reaction is in the current student channel
        guild = cast(discord.Guild, self.bot.get_guild(payload.guild_id))
        channel = cast(discord.TextChannel, guild.get_channel(payload.channel_id))
        message = await channel.fetch_message(payload.message_id)

        if channel.id == Meta.CURRENT_STUDENT_CHANNEL.value:
            return await remove_reaction()

        # ignore if anyone has already reacted to this message
        if any(
            reaction.count > 1
            and isinstance(reaction.emoji, discord.PartialEmoji)
            and reaction.emoji.id == Meta.SNOWPEA.value
            for reaction in message.reactions
        ):
            return await remove_reaction()

        # decline if author is a prospective student
        author = cast(discord.Member, message.author)
        if any(role.id == Role.PROSPECTIVE_STUDENT.value for role in author.roles):
            return await remove_reaction()

        # replace reaction with own reaction
        await message.clear_reaction(
            emoji=PartialEmoji(name="snowpea", id=Meta.SNOWPEA.value)
        )
        await message.add_reaction(
            discord.PartialEmoji(name="snowpea", id=Meta.SNOWPEA.value)
        )

        current_student_channel = cast(
            discord.TextChannel, guild.get_channel(Meta.CURRENT_STUDENT_CHANNEL.value)
        )
        await current_student_channel.send(
            f"{author.mention} please resume your conversation {message.jump_url} here"
        )

    @override
    async def cog_unload(self):
        self.bot.tree.remove_command(
            self.snowpea_context.name, type=self.snowpea_context.type
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Snowpea(bot))
