import os
from typing import cast, override

import discord
from discord import app_commands
from discord.ext import commands

from utils.ids import Meta, Role
from utils.verify.views import VerifyButton, VerifyLayoutView
from web.oauth import OAuthManager
from web.server import OAuthServer


class Verify(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.oauth_manager: OAuthManager = OAuthManager()
        self.oauth_server: OAuthServer = OAuthServer(
            bot, int(os.getenv("PORT", default=8080))
        )

        self.verification_layout: VerifyLayoutView = VerifyLayoutView(self.oauth_server)
        self.bot.loop.create_task(self._init_oauth())

    async def _init_oauth(self) -> None:
        try:
            await self.oauth_manager.connect()
            self.oauth_server.start_server()

            self.bot.add_view(self.verification_layout)

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

    @commands.hybrid_command(
        name="setup_verification",
        description="Set up the persistent verification message.",
    )
    @app_commands.guilds(Meta.SERVER.value)
    @commands.is_owner()
    async def setup_verification(self, ctx: commands.Context[commands.Bot]):
        await ctx.send(view=self.verification_layout)

    @app_commands.command(
        name="verify", description="Verify yourself with your Andrew ID."
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

        view = discord.ui.View(timeout=300)
        verification_url = self.oauth_server.get_verification_url(interaction.user.id)
        oauth_button: discord.ui.Button[discord.ui.View] = discord.ui.Button(
            label="Verify with Andrew ID",
            url=verification_url,
            style=discord.ButtonStyle.link,
        )
        view.add_item(oauth_button)

        await interaction.response.send_message(view=view, ephemeral=True)

    @commands.hybrid_command(
        name="unverify", description="Remove verification from a user."
    )
    @app_commands.describe(user="The Discord user to unverify")
    @app_commands.guilds(Meta.SERVER.value)
    @commands.has_any_role(Role.ADMIN.value, Role.MOD.value)
    async def unverify(self, ctx: commands.Context[commands.Bot], user: discord.Member):
        try:
            # check if user has an andrewid
            andrewid = await self.oauth_manager.get_andrewid(user.id)
            if not andrewid:
                await ctx.reply(f"{user.mention} is not verified.", ephemeral=True)
                return

            # remove andrewid from database
            await self.oauth_manager.delete(f"user:{user.id}")
            await self.oauth_manager.delete(f"andrewid:{andrewid}")

            # update roles
            guild = cast(discord.Guild, self.bot.get_guild(Meta.SERVER.value))
            unverified_role = cast(discord.Role, guild.get_role(Role.UNVERIFIED.value))
            verified_role = cast(discord.Role, guild.get_role(Role.VERIFIED.value))

            if unverified_role not in user.roles:
                await user.add_roles(unverified_role)

            if verified_role in user.roles:
                await user.remove_roles(verified_role)

            await ctx.reply(f"{user.mention} has been unverified.", ephemeral=True)

        except Exception as e:
            await ctx.reply(f"Error unverifying user: {str(e)}", ephemeral=True)

    @commands.hybrid_command(
        name="ban", description="Andrew ID ban either a user or an Andrew ID."
    )
    @app_commands.describe(
        user="A verified Discord user to Andrew ID ban",
        andrewid="An Andrew ID to ban future Discord users with",
        reason="Reason for the ban",
    )
    @app_commands.guilds(Meta.SERVER.value)
    @app_commands.guild_only()
    @commands.has_any_role(Role.ADMIN.value)
    async def ban(
        self,
        ctx: commands.Context[commands.Bot],
        user: discord.Member | None,
        andrewid: str | None,
        reason: str | None,
    ):
        reason = reason or "No reason provided"

        try:
            # ensure the command is used in a guild
            if not ctx.guild or ctx.guild.id != Meta.SERVER.value:
                await ctx.reply(
                    "oops! this command can only be used in the server.", ephemeral=True
                )
                return

            # ensure at least one of user or andrewid is provided
            if not user and not andrewid:
                await ctx.reply(
                    "oops! you must specify either a verified user or an Andrew ID to ban.",
                    ephemeral=True,
                )
                return

            if user:
                user_andrewid = await self.oauth_manager.get_andrewid(user.id)

                # if user is provided, ensure they are verified
                if not user_andrewid:
                    await ctx.reply(
                        f"oops! {user.mention} is not verified, so you can't ban their Andrew ID.",
                        ephemeral=True,
                    )
                    return

                # if both user and andrewid are provided, ensure they match
                if andrewid and user_andrewid != andrewid:
                    await ctx.reply(
                        "oops! the specified user does not match the provided Andrew ID.",
                        ephemeral=True,
                    )
                    return

                # ban the user
                await self.oauth_manager.ban_andrewid(user_andrewid, reason)
                await user.ban(reason=reason, delete_message_days=0)
                await ctx.reply(f"{user.mention} (`{user_andrewid}`) has been banned.")
            elif andrewid:
                await self.oauth_manager.ban_andrewid(andrewid, reason)

                # if someone with this Andrew ID is in the server, ban them
                potential_user = await self.oauth_manager.get_user_by_andrewid(andrewid)
                if potential_user:
                    queried_user = ctx.guild.get_member(potential_user)

                    if queried_user:
                        await ctx.guild.ban(
                            user=queried_user, reason=reason, delete_message_days=0
                        )
                        await ctx.reply(
                            f"{queried_user.mention} (`{andrewid}`) has been banned."
                        )
                        return

                await ctx.reply(f"`{andrewid}` has been banned.")

        except Exception as e:
            await ctx.reply(f"Error banning user: {str(e)}", ephemeral=True)

    @setup_verification.error
    @unverify.error
    @ban.error
    async def verify_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ):
        if isinstance(error, commands.CheckFailure):
            await ctx.reply(
                "oops! you don't have permission to use this command.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Verify(bot))
