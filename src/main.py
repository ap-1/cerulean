import os
import sys
import traceback

import discord
from discord import app_commands

from io import StringIO
from map import prog_to_parser

ALLOWED_GUILDS = [1189987436835643432]  # , 1174113338343559269]
GUILD_HOSTNAMES = ["testing"]  # , "cmu2028"]


def get_names(interaction: discord.Interaction):
    idx = ALLOWED_GUILDS.index(interaction.guild_id)

    hostname = GUILD_HOSTNAMES[idx]
    username = interaction.user.display_name

    return hostname, username


class Terminal(discord.ui.Modal, title="Terminal"):
    input = discord.ui.TextInput(
        label="Command",
        placeholder="Enter your command",
        style=discord.TextStyle.short,
    )

    def __init__(self, *args, history, hostname, cleared, **kwargs):
        super().__init__(*args, **kwargs)

        self.history = history
        self.hostname = hostname
        self.cleared = cleared

    async def run_command(
        self, parse, args: list[str], interaction: discord.Interaction
    ):
        out_buffer = StringIO()
        sys.stdout = out_buffer

        err_buffer = StringIO()
        sys.stderr = err_buffer

        try:
            result = await parse(args, self, interaction) or ""
        except SystemExit:
            print(err_buffer.getvalue().rstrip("\n"))
        finally:
            output = out_buffer.getvalue()
            out_buffer.close()
            err_buffer.close()

            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

            self.history += f"{result}" if output == "" else output.rstrip("\n")

    async def on_submit(self, interaction: discord.Interaction):
        if not self.cleared:
            self.history += f"\n\n{interaction.user.display_name}@{self.hostname}:~$ "

        self.history += f"{self.input.value}\n"
        self.cleared = False

        command, *args = self.input.value.split(" ")
        parse = prog_to_parser.get(command)

        if parse:
            await self.run_command(parse, args, interaction)
        else:
            self.history += f"cmd not found: {command}"

        await interaction.response.edit_message(
            content=f"```bash\n{self.history}```",
            view=Confirm(
                history=self.history,
                hostname=self.hostname,
                cleared=self.cleared,
            ),
        )

    async def on_error(self, interaction: discord.Interaction, err: Exception) -> None:
        info = traceback.format_exception(type(err), err, err.__traceback__)
        terminal = f"```bash\n{self.history}Something went wrong:\n\n{''.join(info)}```"

        await interaction.response.edit_message(content=terminal, view=None)


class Confirm(discord.ui.View):
    def __init__(self, *args, history="", hostname, cleared, **kwargs):
        super().__init__(*args, **kwargs)

        self.history = history
        self.hostname = hostname
        self.cleared = cleared

    @discord.ui.button(label="Open terminal", style=discord.ButtonStyle.primary)
    async def open(self, interaction: discord.Interaction, btn: discord.ui.Button):
        modal = Terminal(
            history=self.history, hostname=self.hostname, cleared=self.cleared
        )

        await interaction.response.send_modal(modal)
        self.stop()

    @discord.ui.button(label="Exit", style=discord.ButtonStyle.secondary)
    async def interrupt(self, interaction: discord.Interaction, btn: discord.ui.Button):
        hostname, username = get_names(interaction)

        command = f"\n{username}@{hostname}:~$ exit"
        terminal = f"```bash\n{self.history}\n{command}\nInterrupt signal received```"

        await interaction.response.edit_message(content=terminal, view=None)
        self.stop()


class Client(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.all()
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        self.allowed_guilds = list(map(discord.Object, ALLOWED_GUILDS))

    async def on_ready(self):
        print(f"Logged in as {self.user}")

    async def setup_hook(self) -> None:
        for guild in self.allowed_guilds:
            await self.tree.sync(guild=guild)

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if (
            payload.guild_id not in ALLOWED_GUILDS
            or payload.event_type != "REACTION_ADD"
        ):
            return

        channel = self.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if message.author == self.user:
            return

        await message.reply(
            mention_author=False,
            content=f'"{message.content}" - {message.author.display_name}\nQuoted by {payload.member.display_name}',
            allowed_mentions=discord.AllowedMentions.none(),
        )


client = Client()


@client.tree.command(guilds=client.allowed_guilds, description="Open the terminal")
async def terminal(interaction: discord.Interaction):
    hostname, username = get_names(interaction)

    await interaction.response.send_message(
        content=f"```bash\n{username}@{hostname}:~$ ```",
        view=Confirm(hostname=hostname, cleared=False),
    )


client.run(os.getenv("TOKEN"))
