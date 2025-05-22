import asyncio
import os
import time
from typing import cast, override

import discord
from discord import app_commands
from discord.ext import commands
from mcstatus import JavaServer
from mcstatus.status_response import JavaStatusResponse

from utils.ids import Meta
from utils.redis import RedisManager


class MinecraftTracker(RedisManager):
    def __init__(self) -> None:
        super().__init__(key_prefix="minecraft")

    async def get_last_status(self) -> bool | None:
        status_str = await self.get("last_status")
        if status_str is None:
            # never checked before
            return None

        return status_str == "online"

    async def set_last_status(self, is_online: bool) -> None:
        await self.set("last_status", "online" if is_online else "offline")

    async def get_last_check_time(self) -> int:
        time_str = await self.get("last_check")
        if time_str is None:
            return 0

        return int(time_str)

    async def set_last_check_time(self, timestamp: int) -> None:
        await self.set("last_check", str(timestamp))


class Minecraft(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.server_host: str = os.getenv("MINECRAFT_SERVER_HOST", "localhost")
        self.server_port: int = int(os.getenv("MINECRAFT_SERVER_PORT", "25565"))

        self.tracker: MinecraftTracker = MinecraftTracker()
        self.check_interval: int = 60  # check every 60 seconds

        self.bot.loop.create_task(self.tracker.connect())
        self.bot.loop.create_task(self.monitor_server())

    async def monitor_server(self) -> None:
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            try:
                # check current server status
                is_online = await self.check_server_status()
                last_status = await self.tracker.get_last_status()
                current_time = int(time.time())

                # if status changed, send notification
                if last_status is not None and last_status != is_online:
                    await self.send_status_notification(is_online)

                # update stored status and check time
                await self.tracker.set_last_status(is_online)
                await self.tracker.set_last_check_time(current_time)

            except Exception as e:
                print(f"Error in Minecraft monitor: {e}")

            # wait before next check
            await asyncio.sleep(self.check_interval)

    async def check_server_status(self) -> bool:
        try:
            server = JavaServer.lookup(f"{self.server_host}:{self.server_port}")
            await server.async_status()

            return True
        except Exception:
            return False

    async def send_status_notification(self, is_online: bool) -> None:
        try:
            guild = cast(discord.Guild, self.bot.get_guild(Meta.SERVER.value))
            channel = cast(
                discord.TextChannel, guild.get_channel(Meta.MINECRAFT_CHANNEL.value)
            )

            if is_online:
                embed = discord.Embed(
                    title="Server online",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow(),
                )
                embed.set_footer(text=f"Server IP: `{self.server_host}`")
            else:
                owner_id = cast(int, self.bot.owner_id)
                owner = cast(discord.Member, guild.get_member(owner_id))

                await channel.send(f"{owner.mention}")

                embed = discord.Embed(
                    title="Server offline",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow(),
                )

            await channel.send(embed=embed)

        except Exception as e:
            print(f"Error sending Minecraft notification: {e}")

    @commands.hybrid_command(
        name="minecraft", description="Check the status of the Minecraft server"
    )
    @app_commands.guilds(Meta.SERVER.value)
    async def minecraft_status(self, ctx: commands.Context[commands.Bot]):
        await ctx.defer()

        try:
            server = JavaServer.lookup(f"{self.server_host}:{self.server_port}")
            status: JavaStatusResponse = await server.async_status()

            embed = discord.Embed(
                title="Server online",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow(),
            )

            # include server info
            embed.add_field(
                name="Players",
                value=f"{status.players.online}/{status.players.max}",
                inline=True,
            )
            embed.add_field(
                name="Latency",
                value=f"{status.latency:.1f}ms",
                inline=True,
            )

            if status.players.online == 0:
                embed.add_field(
                    name="Players",
                    value="No players online",
                    inline=False,
                )
            elif status.players.sample:
                player_names = [player.name for player in status.players.sample]
                
                if len(player_names) <= 15:
                    # show all players inline if not too many
                    embed.add_field(
                        name="Players",
                        value="\n".join(f"• {name}" for name in player_names),
                        inline=False,
                    )
                else:
                    # show first 15 players and indicate there are more
                    displayed_names = player_names[:15]
                    remaining = status.players.online - 15
                    player_list = "\n".join(f"• {name}" for name in displayed_names)
                    
                    if remaining > 0:
                        player_list += f"\n... and {remaining} more"
                    
                    embed.add_field(
                        name="Players",
                        value=player_list,
                        inline=False,
                    )
            elif status.players.online > 0:
                # players online but no sample available
                embed.add_field(
                    name="Players",
                    value=f"{status.players.online} players online\n*(player list not available)*",
                    inline=False,
                )

            embed.set_footer(text=f"Server IP: `{self.server_host}`")

        except (TimeoutError, ConnectionRefusedError):
            embed = discord.Embed(
                title="Server offline",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow(),
            )

        except Exception as e:
            embed = discord.Embed(
                title="Unknown status",
                color=discord.Color.yellow(),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(
                name="Error",
                value=f"```{str(e)[:1000]}```",
                inline=False,
            )

        await ctx.reply(embed=embed)

    @override
    async def cog_unload(self) -> None:
        try:
            await self.tracker.close()
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Minecraft(bot))
