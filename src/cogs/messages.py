import time

import discord
from discord import app_commands
from discord.ext import commands
from pony.orm import db_session

from utils.ids import Role
from utils.messages.models import Mention, Message
from utils.messages.utils import render_progress_bar


class Messages(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    async def index_message(self, message: discord.Message):
        # thread + channel logic
        if isinstance(message.channel, discord.Thread):
            thread_id = message.channel.id
            channel_id = message.channel.parent_id
        else:
            thread_id = None
            channel_id = message.channel.id

        reply_id = (
            message.reference.message_id  # ty: ignore[possibly-unbound-attribute]
            if message.reference
            else None
        )
        mentioned_ids = [user.id for user in message.mentions]

        if not Message.exists(message_id=message.id):
            db_msg = Message(
                message_id=message.id,
                author_id=message.author.id,
                is_bot=message.author.bot,
                channel_id=channel_id,
                thread_id=thread_id,
                content=message.content,
                timestamp=message.created_at,
                reply_to=reply_id,
            )

            for uid in mentioned_ids:
                Mention(mentioned_user_id=uid, message=db_msg)

    @commands.hybrid_command(name="index", description="Index a channel's messages")
    @app_commands.describe(
        channel="Channel to index",
        count="Approximate number of messages for progress bar",
    )
    @commands.has_any_role(Role.ADMIN.value)
    async def index(
        self,
        ctx: commands.Context[commands.Bot],
        channel: discord.TextChannel,
        count: int,
    ):
        await ctx.defer()
        start_time = time.time()
        processed = 0

        progress_embed = discord.Embed(
            title=f"Indexing {channel.name}",
            description="Starting...",
            color=discord.Color.orange(),
        )
        progress_embed.set_footer(text="Elapsed: 0s")
        progress_message = await ctx.reply(embed=progress_embed)

        async def update_embed():
            progress_bar = render_progress_bar(processed, count)
            progress_embed.description = f"{progress_bar}\n{processed}/{count} messages"
            progress_embed.set_footer(text=f"Elapsed: {int(time.time() - start_time)}s")

            await progress_message.edit(embed=progress_embed)

        with db_session:
            async for message in channel.history(limit=None, oldest_first=True):
                await self.index_message(message)
                processed += 1

                if processed % 100 == 0:
                    await update_embed()

        progress_embed.description = f"Done! Indexed {processed} messages."
        progress_embed.color = discord.Color.green()
        progress_embed.set_footer(
            text=f"Total time: {int(time.time() - start_time)} seconds"
        )

        await progress_message.edit(embed=progress_embed)

    @index.error
    async def autoresponse_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.MissingAnyRole):
            await ctx.reply(
                "oops! you don't have permission to index channels.",
                ephemeral=True,
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        with db_session:
            await self.index_message(message)

        await self.bot.process_commands(message)
