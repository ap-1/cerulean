import secrets
from typing import cast

import discord
from discord.ext import commands

from utils.ids import Meta, Role
from utils.redis import RedisManager


class OAuthManager(RedisManager):
    def __init__(self) -> None:
        super().__init__(key_prefix="oauth")

    async def create_verification_session(self, user_id: int) -> str:
        """Create a new verification session and return a state token"""

        state = secrets.token_urlsafe(32)
        await self.set(f"session:{state}", str(user_id), ex=600)  # 10 minute expiry
        return state

    async def get_user_from_state(self, state: str) -> int | None:
        """Get user ID from state token"""

        user_id_str = await self.get(f"session:{state}")
        if user_id_str:
            return int(user_id_str)

        return None

    async def store_andrewid(self, user_id: int, andrewid: str) -> None:
        """Store andrewid for a user"""

        await self.set(f"user:{user_id}", andrewid)
        await self.set(f"andrewid:{andrewid}", str(user_id))

    async def get_andrewid(self, user_id: int) -> str | None:
        """Get andrewid for a user"""

        return await self.get(f"user:{user_id}")

    async def get_user_by_andrewid(self, andrewid: str) -> int | None:
        """Get user ID by andrewid"""

        user_id_str = await self.get(f"andrewid:{andrewid}")
        if user_id_str:
            return int(user_id_str)

        return None

    async def complete_discord_verification(
        self, bot: commands.Bot, user_id: int, andrewid: str
    ):
        """Complete the Discord verification process"""

        try:
            guild = bot.get_guild(Meta.SERVER.value)
            if not guild:
                return

            member = guild.get_member(user_id)
            if not member:
                return

            # remove unverified role
            unverified_role = guild.get_role(Role.UNVERIFIED.value)
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role)

            # log verification
            channel = cast(
                discord.TextChannel, guild.get_channel(Meta.VERIFICATIONS_CHANNEL.value)
            )
            if channel:
                embed = discord.Embed(
                    title="AndrewID Verified",
                    color=discord.Color.green(),
                )
                embed.add_field(
                    name="Discord",
                    value=f"{member.mention} ({member.id})",
                    inline=False,
                )
                embed.add_field(name="AndrewID", value=f"{andrewid}", inline=False)
                await channel.send(embed=embed)

        except Exception as e:
            print(f"Error completing Discord verification: {e}")
