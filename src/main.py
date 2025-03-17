import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.ids import Meta

load_dotenv()

token = os.getenv("DISCORD_TOKEN")
if token is None:
    raise ValueError("DISCORD_TOKEN environment variable not set")


intents = discord.Intents.all()
bot = commands.Bot(command_prefix="c!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    try:
        synced = await bot.tree.sync(guild=discord.Object(id=Meta.SERVER.value))
        synced_names = [cmd.name for cmd in synced]

        print(f"Synced commands: {synced_names}")
    except Exception as e:
        print(f"Error syncing commands: {e}")


async def main(token: str):
    async with bot:
        await bot.load_extension("cogs.general")
        await bot.load_extension("cogs.snowpea")
        await bot.load_extension("cogs.verify")
        await bot.load_extension("cogs.leave")
        await bot.load_extension("cogs.tags")

        await bot.start(token=token)


asyncio.run(main(token))
