import os
import sys
import traceback

import discord
from discord import app_commands

from io import StringIO
from builtin.quote import quote_reaction_handler
from map import prog_to_parser

ALLOWED_GUILDS = [1189987436835643432]  # , 1174113338343559269]
GUILD_HOSTNAMES = ["testing"]  # , "cmu2028"]


def get_prompt(interaction: discord.Interaction):
    idx = ALLOWED_GUILDS.index(interaction.guild_id)

    hostname = GUILD_HOSTNAMES[idx]
    username = interaction.user.display_name

    return f"\n\n{username}@{hostname}:~$ "


class Terminal(discord.ui.Modal, title="Terminal"):
    input = discord.ui.TextInput(
        label="Command",
        placeholder="Enter your command",
        style=discord.TextStyle.short,
    )

    def __init__(self, *args, history, cleared, **kwargs):
        super().__init__(*args, **kwargs)

        self.history = history
        self.cleared = cleared

    # For access within command parsers
    def get_prompt(self, interaction: discord.Interaction):
        return get_prompt(interaction)

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
            self.history += get_prompt(interaction)

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
                cleared=self.cleared,
            ),
        )

    async def on_error(self, interaction: discord.Interaction, err: Exception) -> None:
        info = traceback.format_exception(type(err), err, err.__traceback__)
        terminal = f"```bash\n{self.history}Something went wrong:\n\n{''.join(info)}```"

        await interaction.response.edit_message(content=terminal, view=None)


class Confirm(discord.ui.View):
    def __init__(self, *args, history="", cleared, **kwargs):
        super().__init__(*args, **kwargs)

        self.history = history
        self.cleared = cleared

    @discord.ui.button(label="Open terminal", style=discord.ButtonStyle.primary)
    async def open(self, interaction: discord.Interaction, btn: discord.ui.Button):
        modal = Terminal(history=self.history, cleared=self.cleared)

        await interaction.response.send_modal(modal)
        self.stop()

    @discord.ui.button(label="Clear", style=discord.ButtonStyle.secondary)
    async def clear(self, interaction: discord.Interaction, btn: discord.ui.Button):
        self.history = get_prompt(interaction).lstrip("\n\n")
        self.cleared = True

        terminal = f"```bash\n{self.history}```"

        await interaction.response.edit_message(
            content=terminal, view=Confirm(history=self.history, cleared=self.cleared)
        )

    @discord.ui.button(label="Exit", style=discord.ButtonStyle.danger)
    async def interrupt(self, interaction: discord.Interaction, btn: discord.ui.Button):
        command = f"{get_prompt(interaction)}exit"
        terminal = f"```bash\n{self.history}{command}\nInterrupt signal received```"

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

        await quote_reaction_handler(self, payload)


client = Client()


@client.tree.command(guilds=client.allowed_guilds, description="Open the terminal")
async def terminal(interaction: discord.Interaction):
    command = get_prompt(interaction)

    await interaction.response.send_message(
        content=f"```bash{command}```", view=Confirm(cleared=False)
    )


client.run(os.getenv("TOKEN"))
