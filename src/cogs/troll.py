import random

import discord
from discord.ext import commands

from utils.ids import UNDESIRABLES


class Troll(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id in UNDESIRABLES:
            if random.random() < 0.33:
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Troll(bot))
