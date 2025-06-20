import time

import discord
from discord import app_commands
from discord.ext import commands
from pony.orm import db_session

from utils.ids import Meta, Role
from utils.messages.utils import index_message_sync, render_progress_bar


class Messages(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @commands.hybrid_command(name="index", description="Index a channel's messages")
    @app_commands.describe(
        channel="Channel to index",
        count="Approximate number of messages for progress bar",
    )
    @app_commands.guilds(Meta.SERVER.value)
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

        BATCH_SIZE = 100
        buffer: list[discord.Message] = []

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

        async for message in channel.history(limit=None, oldest_first=True):
            buffer.append(message)
            processed += 1

            if len(buffer) >= BATCH_SIZE:
                with db_session:
                    index_message_sync(message)
                    processed += 1

                buffer.clear()
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
            index_message_sync(message)

        await self.bot.process_commands(message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Messages(bot))
