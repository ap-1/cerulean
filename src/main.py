import os
import sys
import discord
import traceback

from io import StringIO
from builtin.map import prog_to_parser

ALLOWED_GUILDS = [1189987436835643432, 1174113338343559269]
GUILD_HOSTNAMES = ["testing", "cmu2028"]


class Terminal(discord.ui.Modal, title="Terminal"):
    input = discord.ui.TextInput(
        label="Command",
        placeholder="Enter your command",
        style=discord.TextStyle.short,
    )

    def __init__(self, *args, history, hostname, **kwargs):
        super().__init__(*args, **kwargs)

        self.history = history
        self.hostname = hostname

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        command = self.input.value

        self.history += f"{user.display_name}@{self.hostname}:~$ {command}\n"
        self.history += f"{await parse_command(self, interaction)}\n"

        await interaction.response.edit_message(
            content=f"```bash\n{self.history}```",
            view=Confirm(history=self.history + "\n", hostname=self.hostname),
        )

    async def on_error(self, interaction: discord.Interaction, err: Exception) -> None:
        info = traceback.format_exception(type(err), err, err.__traceback__)
        terminal = f"```bash\n{self.history}Something went wrong:\n\n{''.join(info)}```"

        await exit_command(terminal, interaction)


class Confirm(discord.ui.View):
    def __init__(self, *args, history="", hostname, **kwargs):
        super().__init__(*args, **kwargs)

        self.history = history
        self.hostname = hostname

    @discord.ui.button(label="Open terminal", style=discord.ButtonStyle.primary)
    async def open(self, interaction: discord.Interaction, btn: discord.ui.Button):
        modal = Terminal(history=self.history, hostname=self.hostname)

        await interaction.response.send_modal(modal)
        self.stop()

    @discord.ui.button(label="Exit", style=discord.ButtonStyle.secondary)
    async def interrupt(self, interaction: discord.Interaction, btn: discord.ui.Button):
        terminal = f"```bash\n{self.history}Interrupt signal received```"

        await exit_command(terminal, interaction)
        self.stop()


class Client(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user}")

    async def on_message(self, message: discord.Message):
        try:
            idx = ALLOWED_GUILDS.index(message.guild.id)

            hostname = GUILD_HOSTNAMES[idx]
            username = message.author.display_name

            if self.user.mentioned_in(message):
                await message.reply(
                    mention_author=False,
                    content=f"```bash\n{username}@{hostname}:~$ ```",
                    view=Confirm(hostname=hostname),
                )
        except ValueError:
            return


async def parse_command(modal: Terminal, interaction: discord.Interaction):
    command, *args = modal.input.value.split(' ')
    parse = prog_to_parser.get(command)

    if not parse:
        return f"cmd not found: {command}"

    out_buffer = StringIO()
    sys.stdout = out_buffer

    err_buffer = StringIO()
    sys.stderr = err_buffer

    try:
        result = parse(args)
    except SystemExit:
        print(err_buffer.getvalue().rstrip("\n"))
    finally:
        output = out_buffer.getvalue()
        out_buffer.close()
        err_buffer.close()

        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        return result if output == "" else output.rstrip("\n")


async def exit_command(terminal: str, interaction: discord.Interaction):
    await interaction.response.edit_message(content=terminal, view=None)


client = Client(intents=discord.Intents.all())
client.run(os.getenv("TOKEN"))
