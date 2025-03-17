import asyncio
import datetime
from typing import cast, override

import discord
from discord import app_commands
from discord.ext import commands

from utils.ids import Meta, Role
from utils.tag_database import TagDatabase
from utils.tag_models import TagData
from utils.tag_utils import fuzzy_search


def is_mod_or_admin(interaction: discord.Interaction) -> bool:
    if not interaction.user:
        return False

    member = interaction.user
    if isinstance(member, discord.User):
        guild = cast(discord.Guild, interaction.client.get_guild(Meta.SERVER.value))
        member = guild.get_member(member.id)
        if not member:
            return False

    return any(role.id in [Role.ADMIN.value, Role.MOD.value] for role in member.roles)


async def mod_or_admin_check(interaction: discord.Interaction) -> bool:
    has_permission = is_mod_or_admin(interaction)
    if not has_permission:
        await interaction.response.send_message(
            "you don't have permission to use this command", ephemeral=True
        )
        return False

    return True


class TagNameModal(discord.ui.Modal, title="Create Tag"):
    """Modal for getting the tag name when creating a tag."""

    name: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Tag name",
        placeholder="Enter a name for this tag",
        required=True,
        min_length=1,
        max_length=20,
    )

    def __init__(self, cog: "Tags", message: discord.Message) -> None:
        super().__init__()
        self.cog: "Tags" = cog
        self.message: discord.Message = message

    @override
    async def on_submit(self, interaction: discord.Interaction) -> None:
        tag_name = self.name.value.lower()

        # check if tag name already exists
        if tag_name in self.cog.tags:
            await interaction.response.send_message(
                f"a tag with the name '{tag_name}' already exists", ephemeral=True
            )
            return

        # create the new tag
        author = self.message.author
        author_name = (
            author.display_name if hasattr(author, "display_name") else str(author)
        )

        tag = TagData(
            name=tag_name,
            content=self.message.content,
            author_id=author.id,
            author_name=author_name,
            created_at=datetime.datetime.now(),
        )

        try:
            # add tag to database and memory
            await self.cog.db.add_tag(tag)
            self.cog.tags[tag_name] = tag
            await interaction.response.send_message(
                f"tag '{tag_name}' has been created successfully", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"error creating tag '{tag_name}': {str(e)}", ephemeral=True
            )


class Tags(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.db: TagDatabase = TagDatabase()
        self.tags: dict[str, TagData] = {}
        self._ready: asyncio.Event = asyncio.Event()

        # create context menu
        self.create_tag_context: app_commands.ContextMenu = app_commands.ContextMenu(
            name="Create Tag",
            callback=self.create_tag_callback,
            guild_ids=[Meta.SERVER.value],
        )
        self.create_tag_context.add_check(mod_or_admin_check)
        self.bot.tree.add_command(self.create_tag_context)

        # schedule the loading of tags
        self.bot.loop.create_task(self.load_tags())

    async def load_tags(self) -> None:
        try:
            await self.db.connect()
            self.tags = await self.db.get_all_tags()
            self._ready.set()
        except Exception as e:
            # propagate the error instead of falling back to empty tags
            # this will prevent the bot from running if Redis is unavailable
            self._ready.set()
            raise RuntimeError(f"Failed to initialize tag database: {e}")

    async def wait_until_ready(self) -> None:
        await self._ready.wait()

    async def create_tag_callback(
        self, interaction: discord.Interaction, message: discord.Message
    ) -> None:
        await self.wait_until_ready()

        # create a modal to get the tag name
        modal = TagNameModal(cog=self, message=message)
        await interaction.response.send_modal(modal)

    @commands.hybrid_command(name="tag", description="Display a saved tag.")
    @app_commands.guilds(Meta.SERVER.value)
    @app_commands.describe(name="The name of the tag to display")
    async def tag(self, ctx: commands.Context[commands.Bot], name: str) -> None:
        await self.wait_until_ready()
        name = name.lower()

        if name in self.tags:
            # found exact match
            tag = self.tags[name]
            await self._display_tag(ctx, tag)
        else:
            search_results = fuzzy_search(name, self.tags, threshold=0.6)

            if not search_results:
                # no similar tags found
                await ctx.reply(f"Tag '{name}' not found.", ephemeral=True)
            elif len(search_results) == 1 and search_results[0][1] > 0.8:
                # single high-confidence match, display it directly
                result_name = search_results[0][0]
                tag = self.tags[result_name]

                await self._display_tag(ctx, tag)
            else:
                # multiple possible matches, suggest the top 5
                suggestions = ", ".join(
                    f"`{result[0]}`" for result in search_results[:5]
                )
                await ctx.reply(
                    f"Tag '{name}' not found. Did you mean one of these?\n{suggestions}",
                    ephemeral=True,
                )

    async def _display_tag(
        self, ctx: commands.Context[commands.Bot], tag: TagData
    ) -> None:
        tag.uses += 1
        try:
            await self.db.update_tag(tag)
        except Exception as e:
            print(f"Error updating tag usage count: {e}")

        author_name = tag.author_name
        try:
            guild = ctx.guild
            if guild:
                # try to fetch the member by ID and update to their current name
                member = guild.get_member(tag.author_id)
                if member:
                    author_name = member.display_name
        except Exception:
            # default to stored name
            pass

        embed = discord.Embed(
            title=f"{'⭐ ' if tag.starred else ''}{tag.name}",
            description=tag.content,
            color=discord.Color.gold() if tag.starred else discord.Color.blue(),
            timestamp=tag.created_at,
        )
        embed.set_footer(
            text=f"Created by {author_name} • Used {tag.uses} time{'s' if tag.uses != 1 else ''}"
        )
        await ctx.reply(embed=embed)

    @commands.hybrid_group(name="tags", description="Manage tags.")
    @app_commands.guilds(Meta.SERVER.value)
    async def tags_group(self, ctx: commands.Context[commands.Bot]) -> None:
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @tags_group.command(name="list", description="List all available tags.")
    async def tags_list(self, ctx: commands.Context[commands.Bot]) -> None:
        await self.wait_until_ready()
        if not self.tags:
            await ctx.reply("no tags have been created yet", ephemeral=True)
            return

        # sort tags
        tag_names = sorted(self.tags.keys())

        starred = [name for name in tag_names if self.tags[name].starred]
        normal = [name for name in tag_names if not self.tags[name].starred]

        embed = discord.Embed(color=discord.Color.blue())

        if starred:
            embed.add_field(
                name="Starred Tags",
                value=", ".join(f"`{name}`" for name in starred),
                inline=False,
            )

        if normal:
            embed.add_field(
                name="Tags",
                value=", ".join(f"`{name}`" for name in normal),
                inline=False,
            )

        star_count = len(starred)
        footer_text = f"Total tags: {len(tag_names)}"

        if star_count > 0:
            footer_text += f" | Starred: {star_count}"

        embed.set_footer(text=footer_text)
        await ctx.reply(embed=embed, ephemeral=True)

    @tags_group.command(
        name="search", description="Search for tags that match a query."
    )
    @app_commands.describe(query="The search term")
    async def tags_search(
        self, ctx: commands.Context[commands.Bot], query: str
    ) -> None:
        await self.wait_until_ready()

        if not self.tags:
            await ctx.reply("no tags have been created yet", ephemeral=True)
            return

        # fuzzy search with lower threshold for search command
        search_results = fuzzy_search(query, self.tags, threshold=0.4)

        if not search_results:
            await ctx.reply(f"no tags found matching '{query}'.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Search results for '{query}'", color=discord.Color.blue()
        )

        # group results by similarity
        high_matches: list[str] = []
        medium_matches: list[str] = []
        low_matches: list[str] = []

        for name, score in search_results:
            display_name = f"⭐ {name}" if self.tags[name].starred else name

            if score > 0.75:
                high_matches.append(f"`{display_name}`")
            elif score > 0.6:
                medium_matches.append(f"`{display_name}`")
            else:
                low_matches.append(f"`{display_name}`")

        if high_matches:
            embed.add_field(
                name="Strong Matches", value=", ".join(high_matches), inline=False
            )

        if medium_matches:
            embed.add_field(
                name="Medium Matches", value=", ".join(medium_matches), inline=False
            )

        if low_matches:
            embed.add_field(
                name="Weak Matches", value=", ".join(low_matches), inline=False
            )

        embed.set_footer(text=f"Found {len(search_results)} matching tags")
        await ctx.reply(embed=embed)

    @tags_group.command(
        name="star",
        description="Star or unstar a tag.",
    )
    @app_commands.describe(name="The name of the tag to star/unstar")
    @commands.has_any_role(Role.ADMIN.value, Role.MOD.value)
    async def tags_star(self, ctx: commands.Context[commands.Bot], name: str) -> None:
        await self.wait_until_ready()
        name = name.lower()

        if name in self.tags:
            try:
                tag = self.tags[name]
                tag.starred = not tag.starred

                # update the tag in the database
                success = await self.db.update_tag(tag)
                if success:
                    status = "starred" if tag.starred else "unstarred"
                    await ctx.reply(f"tag '{name}' has been {status}", ephemeral=True)
                else:
                    await ctx.reply(f"error updating tag '{name}'", ephemeral=True)
            except Exception as e:
                await ctx.reply(
                    f"error starring tag '{name}': {str(e)}", ephemeral=True
                )
        else:
            await ctx.reply(f"tag '{name}' not found", ephemeral=True)

    @tags_star.error
    async def tags_star_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.MissingAnyRole):
            await ctx.reply("you don't have permission to star tags", ephemeral=True)

    @tags_group.command(name="delete", description="Delete a tag.")
    @app_commands.describe(name="The name of the tag to delete")
    @commands.has_any_role(Role.ADMIN.value, Role.MOD.value)
    async def tags_delete(self, ctx: commands.Context[commands.Bot], name: str) -> None:
        await self.wait_until_ready()
        name = name.lower()

        if name in self.tags:
            try:
                # delete from database
                success = await self.db.delete_tag(name)
                if success:
                    # delete from memory if database deletion was successful
                    del self.tags[name]
                    await ctx.reply(f"tag '{name}' has been deleted", ephemeral=True)
                else:
                    await ctx.reply(
                        f"tag '{name}' not found in database", ephemeral=True
                    )
            except Exception as e:
                await ctx.reply(
                    f"error deleting tag '{name}': {str(e)}", ephemeral=True
                )
        else:
            await ctx.reply(f"tag '{name}' not found", ephemeral=True)

    @tags_delete.error
    async def tags_delete_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.MissingAnyRole):
            await ctx.reply("you don't have permission to delete tags", ephemeral=True)

    @override
    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(
            self.create_tag_context.name, type=self.create_tag_context.type
        )
        await self.db.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(Tags(bot))
