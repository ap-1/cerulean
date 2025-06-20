import asyncio
import random
from typing import cast, override

import discord
from discord import app_commands
from discord.ext import commands

from utils.autoresponse.database import AutoresponseDatabase
from utils.autoresponse.models import AutoresponseData
from utils.ids import Meta, Role


class Autoresponse(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.db: AutoresponseDatabase = AutoresponseDatabase()
        self.autoresponses: dict[str, AutoresponseData] = {}
        self._ready: asyncio.Event = asyncio.Event()

        # schedule loading of autoresponses
        self.bot.loop.create_task(self.load_autoresponses())

    async def load_autoresponses(self) -> None:
        try:
            await self.db.connect()
            self.autoresponses = await self.db.get_all_autoresponses()
            self._ready.set()
        except Exception as e:
            self._ready.set()
            raise RuntimeError(f"Failed to initialize autoresponse database: {e}")

    async def wait_until_ready(self) -> None:
        await self._ready.wait()

    @commands.hybrid_group(name="autoresponse", description="Manage autoresponses")
    @app_commands.guilds(Meta.SERVER.value)
    @commands.guild_only()
    async def autoresponse_group(self, ctx: commands.Context[commands.Bot]) -> None:
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @autoresponse_group.command(name="create", description="Create a new autoresponse")
    @app_commands.describe(
        name="Name for the autoresponse",
        probability="Probability (0.0-1.0) that the autoresponse triggers",
        template="Response template, use {trigger} for the matched word",
        triggers="Space-separated list of trigger words",
    )
    @commands.has_any_role(Role.ADMIN.value, Role.MOD.value)
    async def create_autoresponse(
        self,
        ctx: commands.Context[commands.Bot],
        name: str,
        probability: float,
        template: str,
        *,
        triggers: str,
    ) -> None:
        await self.wait_until_ready()

        # validate inputs
        if not 0.0 <= probability <= 1.0:
            await ctx.reply(
                "oops! probability must be between 0.0 and 1.0", ephemeral=True
            )
            return

        name = name.lower()
        if name in self.autoresponses:
            await ctx.reply(
                f"oops! an autoresponse with the name `{name}` already exists",
                ephemeral=True,
            )
            return

        # parse triggers
        trigger_list = [t.strip().lower() for t in triggers.split() if t.strip()]
        if not trigger_list:
            await ctx.reply(
                "oops! you must provide at least one trigger", ephemeral=True
            )
            return

        # create autoresponse
        autoresponse = AutoresponseData(
            name=name,
            probability=probability,
            triggers=trigger_list,
            template=template,
        )

        try:
            await self.db.add_autoresponse(autoresponse)
            self.autoresponses[name] = autoresponse

            embed = discord.Embed(
                title="Autoresponse Created",
                color=discord.Color.green(),
            )
            embed.add_field(name="Name", value=name, inline=True)
            embed.add_field(
                name="Probability", value=f"{probability * 100}%", inline=True
            )
            embed.add_field(
                name="Triggers", value=", ".join(trigger_list), inline=False
            )
            embed.add_field(
                name="Template", value=f"```\n{template}\n```", inline=False
            )

            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"Error creating autoresponse: {str(e)}", ephemeral=True)

    @autoresponse_group.command(name="delete", description="Delete an autoresponse")
    @app_commands.describe(name="Name of the autoresponse to delete")
    @commands.has_any_role(Role.ADMIN.value, Role.MOD.value)
    async def delete_autoresponse(
        self, ctx: commands.Context[commands.Bot], name: str
    ) -> None:
        await self.wait_until_ready()
        name = name.lower()

        if name not in self.autoresponses:
            await ctx.reply(f"oops! autoresponse `{name}` not found", ephemeral=True)
            return

        try:
            success = await self.db.delete_autoresponse(name)
            if success:
                del self.autoresponses[name]
                await ctx.reply(
                    f"autoresponse `{name}` has been deleted", ephemeral=True
                )
            else:
                await ctx.reply(
                    f"autoresponse `{name}` not found in database", ephemeral=True
                )
        except Exception as e:
            await ctx.reply(f"Error deleting autoresponse: {str(e)}", ephemeral=True)

    @autoresponse_group.group(name="set", description="Set autoresponse properties")
    @commands.has_any_role(Role.ADMIN.value, Role.MOD.value)
    async def set_group(self, ctx: commands.Context[commands.Bot]) -> None:
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @set_group.command(
        name="probability", description="Set the probability for an autoresponse"
    )
    @app_commands.describe(
        name="Name of the autoresponse",
        probability="New probability (0.0-1.0)",
    )
    async def set_probability(
        self, ctx: commands.Context[commands.Bot], name: str, probability: float
    ) -> None:
        await self.wait_until_ready()
        name = name.lower()

        if not 0.0 <= probability <= 1.0:
            await ctx.reply(
                "oops! probability must be between 0.0 and 1.0", ephemeral=True
            )
            return

        if name not in self.autoresponses:
            await ctx.reply(f"oops! autoresponse `{name}` not found", ephemeral=True)
            return

        try:
            autoresponse = self.autoresponses[name]
            autoresponse.probability = probability

            await self.db.update_autoresponse(autoresponse)
            await ctx.reply(
                f"set probability for `{name}` to {probability * 100}%", ephemeral=True
            )
        except Exception as e:
            await ctx.reply(f"Error updating probability: {str(e)}", ephemeral=True)

    @set_group.command(
        name="template", description="Set the template for an autoresponse"
    )
    @app_commands.describe(
        name="Name of the autoresponse",
        template="New template, use {trigger} for the matched word",
    )
    async def set_template(
        self, ctx: commands.Context[commands.Bot], name: str, *, template: str
    ) -> None:
        await self.wait_until_ready()
        name = name.lower()

        if name not in self.autoresponses:
            await ctx.reply(f"oops! autoresponse `{name}` not found", ephemeral=True)
            return

        try:
            autoresponse = self.autoresponses[name]
            autoresponse.template = template

            await self.db.update_autoresponse(autoresponse)
            await ctx.reply(
                f"set template for `{name}` to: ```\n{template}\n```", ephemeral=True
            )
        except Exception as e:
            await ctx.reply(f"Error updating template: {str(e)}", ephemeral=True)

    @set_group.command(
        name="triggers", description="Set the triggers for an autoresponse"
    )
    @app_commands.describe(
        name="Name of the autoresponse",
        triggers="Space-separated list of trigger words",
    )
    async def set_triggers(
        self, ctx: commands.Context[commands.Bot], name: str, *, triggers: str
    ) -> None:
        await self.wait_until_ready()
        name = name.lower()

        if name not in self.autoresponses:
            await ctx.reply(f"oops! autoresponse `{name}` not found", ephemeral=True)
            return

        # parse triggers
        trigger_list = [t.strip().lower() for t in triggers.split() if t.strip()]
        if not trigger_list:
            await ctx.reply(
                "oops! you must provide at least one trigger", ephemeral=True
            )
            return

        try:
            autoresponse = self.autoresponses[name]
            autoresponse.triggers = trigger_list

            await self.db.update_autoresponse(autoresponse)
            await ctx.reply(
                f"set triggers for `{name}` to: {', '.join(trigger_list)}",
                ephemeral=True,
            )
        except Exception as e:
            await ctx.reply(f"Error updating triggers: {str(e)}", ephemeral=True)

    @autoresponse_group.command(name="list", description="List all autoresponses")
    async def list_autoresponses(self, ctx: commands.Context[commands.Bot]) -> None:
        await self.wait_until_ready()

        if not self.autoresponses:
            await ctx.reply("no autoresponses have been created yet", ephemeral=True)
            return

        embed = discord.Embed(
            title="Autoresponses",
            color=discord.Color.blue(),
        )

        for name, autoresponse in sorted(self.autoresponses.items()):
            probability_percent = int(autoresponse.probability * 100)
            triggers_str = ", ".join(autoresponse.triggers)
            template_preview = (
                autoresponse.template[:50] + "..."
                if len(autoresponse.template) > 50
                else autoresponse.template
            )

            embed.add_field(
                name=f"`{name}` ({probability_percent}%)",
                value=f"**Triggers:** {triggers_str}\n**Template:** ```\n{template_preview}\n```",
                inline=False,
            )

        await ctx.reply(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # ignore bot messages and messages outside the server
        if (
            message.author.bot
            or not message.guild
            or cast(discord.Guild, message.guild).id != Meta.SERVER.value  # pyright: ignore[reportUnnecessaryCast]
        ):
            return

        await self.wait_until_ready()

        if not self.autoresponses:
            return

        # check message content for triggers
        content_lower = message.content.lower()
        words = content_lower.split()

        for autoresponse in self.autoresponses.values():
            for trigger in autoresponse.triggers:
                # check if trigger appears as a word or substring
                if trigger in words or trigger in content_lower:
                    # check probability
                    if random.random() <= autoresponse.probability:
                        # format template
                        response = autoresponse.template.replace("{trigger}", trigger)

                        try:
                            await message.reply(response)
                            return  # only respond once per message
                        except discord.HTTPException:
                            pass

    @create_autoresponse.error
    @delete_autoresponse.error
    @set_probability.error
    @set_template.error
    @set_triggers.error
    async def autoresponse_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.MissingAnyRole):
            await ctx.reply(
                "oops! you don't have permission to manage autoresponses",
                ephemeral=True,
            )

    @override
    async def cog_unload(self) -> None:
        try:
            await self.db.close()
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Autoresponse(bot))
