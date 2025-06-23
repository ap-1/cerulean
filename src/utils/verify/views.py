from typing import cast, override

import discord
from discord.components import MediaGalleryItem

from utils.ids import Meta
from web.server import OAuthServer


class VerifyButton(discord.ui.Button[discord.ui.LayoutView]):
    def __init__(self, oauth_server: OAuthServer):
        super().__init__(
            label="Verify", style=discord.ButtonStyle.primary, custom_id="verify_button"
        )
        self.oauth_server: OAuthServer = oauth_server

    @override
    async def callback(self, interaction: discord.Interaction):
        guild = cast(discord.Guild, interaction.client.get_guild(Meta.SERVER.value))
        member = guild.get_member(interaction.user.id)
        if not member:
            await interaction.response.send_message(
                content="oops! please join the server and try again.",
                ephemeral=True,
            )
            return

        try:
            andrewid = await self.oauth_server.oauth_manager.get_andrewid(member.id)
            if andrewid:
                await interaction.response.send_message(
                    content=f"oops! you're already verified as `{andrewid}`.",
                    ephemeral=True,
                )
                return
        except Exception as e:
            print(f"Error checking Andrew ID for user {member.id}: {e}")
            pass

        verification_url = self.oauth_server.get_verification_url(interaction.user.id)

        view = discord.ui.View(timeout=300)
        oauth_button: discord.ui.Button[discord.ui.View] = discord.ui.Button(
            label="Verify with Andrew ID",
            url=verification_url,
            style=discord.ButtonStyle.link,
        )
        view.add_item(oauth_button)

        await interaction.response.send_message(view=view, ephemeral=True)


class VerifyContainer(discord.ui.Container[discord.ui.LayoutView]):
    def __init__(self, oauth_server: OAuthServer):
        super().__init__()

        self.add_item(
            discord.ui.MediaGallery(
                MediaGalleryItem(
                    "https://raw.githubusercontent.com/ap-1/cerulean/main/assets/banner.png"
                ),
                row=0,
            )
        )
        self.add_item(discord.ui.TextDisplay("# Welcome!", row=1))
        self.add_item(
            discord.ui.TextDisplay(
                "This server uses Andrew ID verification to restrict access to students and alumni of Carnegie Mellon University.",
                row=2,
            )
        )
        self.add_item(discord.ui.TextDisplay("## How it works", row=3))
        self.add_item(
            discord.ui.TextDisplay(
                (
                    "1. Click on the verification button below\n"
                    "2. Sign in with your CMU Google account\n"
                    "3. Get automatically assigned your roles"
                ),
                row=4,
            )
        )
        self.add_item(discord.ui.Separator(row=5))

        action_row: discord.ui.ActionRow[discord.ui.LayoutView] = discord.ui.ActionRow()
        action_row.add_item(VerifyButton(oauth_server))
        self.add_item(action_row)

        self.add_item(
            discord.ui.TextDisplay(
                "-# Worried about privacy? People will not be able to look up your Andrew ID with your Discord or vice versa. All code is available to audit [here](https://github.com/ap-1/cerulean).",
                row=7,
            )
        )


class VerifyLayoutView(discord.ui.LayoutView):
    def __init__(self, oauth_server: OAuthServer):
        super().__init__(timeout=None)  # persistent view

        self.container: VerifyContainer = VerifyContainer(oauth_server)
        self.add_item(self.container)
