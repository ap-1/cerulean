from typing import cast, override

import discord
from discord import PartialEmoji, app_commands
from discord.ext import commands
from discord.member import Member

from utils.ids import Meta, Role
from utils.tracker import SnowpeaTracker


class Snowpea(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.tracker: SnowpeaTracker = SnowpeaTracker()

        self.bot.loop.create_task(self.tracker.connect())

    @commands.hybrid_group(name="snowpea", description="Snowpea related commands")
    @app_commands.guilds(Meta.SERVER.value)
    @commands.guild_only()
    async def snowpea_group(self, ctx: commands.Context[commands.Bot]) -> None:
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @snowpea_group.command(
        name="stats", description="Show snowpea statistics for a user"
    )
    @commands.guild_only()
    async def snowpea_stats(
        self, ctx: commands.Context[commands.Bot], user: discord.Member | None = None
    ) -> None:
        # default to the invoker if no user is specified
        target_user = user or ctx.author

        received_count = await self.tracker.get_received_count(target_user.id)
        initiated_count = await self.tracker.get_initiated_count(target_user.id)

        embed = discord.Embed(
            title=f"Snowpea Stats for {target_user.display_name}",
            color=discord.Color.green(),
        )

        embed.add_field(
            name="Snowpea'd (Received)",
            value=f"{received_count} time{'s' if received_count != 1 else ''}",
            inline=False,
        )

        embed.add_field(
            name="Snowpea'd Others (Initiated)",
            value=f"{initiated_count} time{'s' if initiated_count != 1 else ''}",
            inline=False,
        )

        await ctx.reply(embed=embed)

    @snowpea_group.command(
        name="leaderboard", description="Show snowpea statistics leaderboard"
    )
    @app_commands.describe(category="The type of leaderboard to show")
    @app_commands.choices(
        category=[
            app_commands.Choice(name="Received (been snowpea'd)", value="received"),
            app_commands.Choice(name="Initiated (snowpea'd others)", value="initiated"),
        ]
    )
    @commands.guild_only()
    async def snowpea_leaderboard(
        self,
        ctx: commands.Context[commands.Bot],
        category: app_commands.Choice[str],
    ) -> None:
        await ctx.defer()

        resolved = category.value.lower()

        # validate category
        if resolved not in ["received", "initiated"]:
            await ctx.reply(
                "invalid category, choose either 'received' or 'initiated'",
                ephemeral=True,
            )
            return

        user_ids = await self.tracker.get_users_with_stats(resolved)

        if not user_ids:
            await ctx.reply("no statistics available yet", ephemeral=True)
            return

        stats: list[tuple[Member, int]] = []
        guild = ctx.guild
        if not guild or not guild.id == Meta.SERVER.value:
            await ctx.reply(
                "this command can only be used in the server", ephemeral=True
            )
            return

        # iterate through these user IDs and get their stats
        for user_id_str in user_ids:
            try:
                user_id = int(user_id_str)
                member = guild.get_member(user_id)
                if not member:
                    # skip users not in the guild
                    continue

                if resolved == "received":
                    count = await self.tracker.get_received_count(member.id)
                else:  # initiated
                    count = await self.tracker.get_initiated_count(member.id)

                if count > 0:
                    # only include users with non-zero counts
                    stats.append((member, count))
            except (ValueError, TypeError):
                # skip invalid user IDs
                continue

        # sort by count in descending order
        stats.sort(key=lambda x: x[1], reverse=True)

        top_users: list[tuple[Member, int]] = stats[:10]
        if not top_users:
            await ctx.reply("no statistics available yet", ephemeral=True)
            return

        embed = discord.Embed(
            title="Wall of Shame" if resolved == "received" else "Wall of Fame",
            color=discord.Color.blue(),
        )

        # add fields for each user
        for i, (member, count) in enumerate(top_users, start=1):
            embed.add_field(
                name=f"{i}. {member.display_name}",
                value=f"{count} time{'s' if count != 1 else ''}",
                inline=False,
            )

        await ctx.reply(embed=embed)

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

        # update statistics
        await self.tracker.increment_received_count(author.id)
        await self.tracker.increment_initiated_count(member.id)

        current_student_channel = cast(
            discord.TextChannel, guild.get_channel(Meta.CURRENT_STUDENT_CHANNEL.value)
        )
        await current_student_channel.send(
            f"{author.mention}, {member.display_name} wants you to resume {message.jump_url} here"
        )

    @override
    async def cog_unload(self) -> None:
        try:
            await self.tracker.close()
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Snowpea(bot))
