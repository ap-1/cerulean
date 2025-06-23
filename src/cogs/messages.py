import asyncio
import time

import discord
from discord import app_commands
from discord.ext import commands

from utils.ids import Meta, Role
from utils.messages.utils import (
    index_edited_message,
    index_messages,
    index_reaction,
    render_progress_bar,
)


class Messages(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @commands.hybrid_command(name="index", description="Index a channel's messages")
    @app_commands.describe(
        channel="Channel to index",
        count="Approximate number of messages for progress bar",
        limit="Optional limit for the number of messages to index (default: all)",
    )
    @app_commands.guilds(Meta.SERVER.value)
    @commands.has_any_role(Role.ADMIN.value)
    async def index(
        self,
        ctx: commands.Context[commands.Bot],
        channel: discord.TextChannel,
        count: int,
        limit: int | None = None,
    ):
        await ctx.send(f"started indexing {channel.mention}", ephemeral=True)
        asyncio.create_task(self._run_index(channel, count, limit))

    async def _run_index(
        self,
        channel: discord.TextChannel,
        count: int,
        limit: int | None,
    ):
        start_time = time.time()
        processed = 0
        count = min(count, limit) if limit is not None else count

        BATCH_SIZE = 100
        buffer: list[discord.Message] = []

        progress_embed = discord.Embed(
            title=f"Indexing {channel.name}",
            description="Starting...",
            color=discord.Color.orange(),
        )
        progress_embed.set_footer(text="Elapsed: 0s")
        progress_message = await channel.send(embed=progress_embed)

        async def process_batch():
            await index_messages(buffer)
            buffer.clear()

            progress_bar = render_progress_bar(processed, count)
            progress_embed.description = f"{progress_bar}\n{processed}/{count} messages"
            progress_embed.set_footer(text=f"Elapsed: {int(time.time() - start_time)}s")

            await progress_message.edit(embed=progress_embed)

        # process messages in batches
        async for message in channel.history(limit=limit, oldest_first=True):
            buffer.append(message)
            processed += 1

            if len(buffer) >= BATCH_SIZE:
                await process_batch()

        # process remaining messages
        if buffer:
            await process_batch()

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
            await ctx.send(
                "oops! you don't have permission to index channels.",
                ephemeral=True,
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await index_messages([message])
        await self.bot.process_commands(message)

    @commands.Cog.listener()
    async def on_message_edit(self, _: discord.Message, after: discord.Message):
        await index_edited_message(after)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await index_reaction(
            message_id=payload.message_id,
            user_id=payload.user_id,
            emoji=payload.emoji,
            action="add",
        )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await index_reaction(
            message_id=payload.message_id,
            user_id=payload.user_id,
            emoji=payload.emoji,
            action="remove",
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Messages(bot))
