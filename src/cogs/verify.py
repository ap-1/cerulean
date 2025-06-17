import os
from typing import cast, override

import discord
from discord import app_commands
from discord.ext import commands

from utils.ids import Meta
from web.oauth import OAuthManager
from web.server import OAuthServer


class Verify(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.oauth_manager: OAuthManager = OAuthManager()
        self.oauth_server: OAuthServer = OAuthServer(
            bot, int(os.getenv("PORT", default=8080))
        )

        self.bot.loop.create_task(self._init_oauth())

    async def _init_oauth(self) -> None:
        try:
            await self.oauth_manager.connect()
            self.oauth_server.start_server()
            print("Started OAuth server")
        except Exception as e:
            print(f"Failed to start OAuth server: {e}")
            raise

    @override
    async def cog_unload(self) -> None:
        try:
            self.oauth_server.stop_server()
            await self.oauth_manager.close()
        except Exception as e:
            print(f"Failed to clean up OAuth: {e}")

    @app_commands.command(
        name="verify", description="Verify yourself with your AndrewID."
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

        try:
            andrewid = await self.oauth_manager.get_andrewid(member.id)
            if andrewid:
                await interaction.response.send_message(
                    content=f"oops! you're already verified as `{andrewid}`.",
                    ephemeral=True,
                )
                return
        except Exception:
            pass

        channel = cast(
            discord.TextChannel, guild.get_channel(Meta.VERIFY_CHANNEL.value)
        )
        if interaction.channel_id != channel.id:
            await interaction.response.send_message(
                content="oops! please use the verification channel.",
                ephemeral=True,
            )
            return

        view = discord.ui.View(timeout=300)
        verification_url = self.oauth_server.get_verification_url(interaction.user.id)
        oauth_button: discord.ui.Button[discord.ui.View] = discord.ui.Button(
            label="Verify with AndrewID",
            url=verification_url,
            style=discord.ButtonStyle.link,
        )
        view.add_item(oauth_button)

        await interaction.response.send_message(view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Verify(bot))
