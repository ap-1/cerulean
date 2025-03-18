from typing import cast

import discord
from discord.ext import commands

from utils.ids import Meta, Role


class Leave(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.guild.id != Meta.SERVER.value:
            return

        if any(role.id == Role.UNVERIFIED.value for role in member.roles):
            dm_message = (
                f"hey {member.display_name},\n"
                "did you know you can `/verify` to get access to the rest of the server?\n"
                "no pressure to rejoin, but if you'd like to come back, you can use this invite:\n"
                "https://discord.gg/UmmbZ8qPbV\n\n"
                "please note that we can't see your response if you reply here!"
            )

            channel = cast(
                discord.TextChannel, self.bot.get_channel(Meta.ADMIN_CHANNEL.value)
            )

            try:
                await member.send(dm_message)
                await channel.send(
                    f"sent DM to {member.display_name} ({member.id}), who left the server and was unverified"
                )
            except discord.Forbidden:
                await channel.send(
                    f"failed to send DM to {member.display_name} ({member.id}), who left the server and was unverified"
                )


async def setup(bot: commands.Bot):
    await bot.add_cog(Leave(bot))
