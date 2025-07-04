import secrets
from typing import cast

import discord
from discord.ext import commands

from utils.directory import DirectoryParser
from utils.ids import Meta, Role
from utils.redis import RedisManager


class OAuthManager(RedisManager):
    def __init__(self) -> None:
        super().__init__(key_prefix="oauth")

    async def create_verification_session(self, user_id: int) -> str:
        # create a new verification session and return a state token
        state = secrets.token_urlsafe(32)
        await self.set(f"session:{state}", str(user_id), ex=300)  # 5 minute expiry

        return state

    async def delete_verification_session(self, state: str) -> None:
        await self.delete(f"session:{state}")

    async def get_user_from_state(self, state: str) -> int | None:
        user_id_str = await self.get(f"session:{state}")
        if user_id_str:
            return int(user_id_str)

        return None

    async def store_andrewid(self, user_id: int, andrewid: str) -> None:
        await self.set(f"user:{user_id}", andrewid)
        await self.set(f"andrewid:{andrewid}", str(user_id))

    async def get_andrewid(self, user_id: int) -> str | None:
        return await self.get(f"user:{user_id}")

    async def get_user_by_andrewid(self, andrewid: str) -> int | None:
        user_id_str = await self.get(f"andrewid:{andrewid}")
        if user_id_str:
            return int(user_id_str)

        return None

    async def ban_andrewid(self, andrewid: str, reason: str) -> None:
        await self.sadd("banned", andrewid)
        await self.set(f"ban:{andrewid}", reason)

    async def is_banned(self, andrewid: str) -> bool:
        return await self.sismember("banned", andrewid)

    async def get_ban_reason(self, andrewid: str) -> str | None:
        return await self.get(f"ban:{andrewid}")

    async def enforce_ban(
        self, bot: commands.Bot, user_id: int, andrewid: str, ban_reason: str
    ):
        try:
            guild = bot.get_guild(Meta.SERVER.value)
            if not guild:
                return

            member = guild.get_member(user_id)
            if not member:
                return

            await member.ban(
                reason=f"Andrew ID {andrewid} is banned: {ban_reason}",
                delete_message_days=0,
            )

            # log to admin channel
            admin_channel = cast(
                discord.TextChannel, bot.get_channel(Meta.ADMIN_CHANNEL.value)
            )
            await admin_channel.send(
                f"banned {member.mention} for having banned Andrew ID {andrewid}. original reason: {ban_reason}"
            )

        except Exception as e:
            print(f"Error enforcing ban: {e}")

    async def complete_verification(
        self, bot: commands.Bot, user_id: int, andrewid: str
    ):
        try:
            guild = bot.get_guild(Meta.SERVER.value)
            if not guild:
                return

            member = guild.get_member(user_id)
            if not member:
                return

            department_roles, class_level_role = await DirectoryParser.lookup_user(
                andrewid
            )

            # remove unverified role
            unverified_role = guild.get_role(Role.UNVERIFIED.value)
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role)

            # remove existing academic roles
            roles_to_remove: list[discord.Role] = []
            all_academic_roles = {
                Role.FIRST_YEAR.value,
                Role.UNDERGRAD.value,
                Role.GRAD.value,
                Role.PHD.value,
                Role.ALUM.value,
                Role.BXA.value,
                Role.CFA.value,
                Role.MCS.value,
                Role.SCS.value,
                Role.CIT.value,
                Role.DIETRICH.value,
                Role.TEPPER.value,
                Role.HEINZ.value,
            }

            for role in member.roles:
                if role.id in all_academic_roles:
                    roles_to_remove.append(role)

            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)

            # add new roles based on directory lookup
            roles_to_add: list[discord.Role] = [
                cast(discord.Role, guild.get_role(Role.VERIFIED.value))
            ]

            for dept_role in department_roles:
                role_obj = guild.get_role(dept_role.value)
                if role_obj:
                    roles_to_add.append(role_obj)

            if class_level_role:
                class_role_obj = guild.get_role(class_level_role.value)
                if class_role_obj:
                    roles_to_add.append(class_role_obj)

            await member.add_roles(*roles_to_add)

        except Exception as e:
            print(f"Error completing Discord verification: {e}")
