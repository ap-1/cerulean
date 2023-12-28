import os
import discord
import traceback

ALLOWED_GUILDS = [1189987436835643432, 1174113338343559269]
GUILD_HOSTNAMES = ["testing", "cmu2028"]


def parse_command(user: discord.User, command: str):
    return "Default output"


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
        self.history += f"{parse_command(user, command)}\n"

        await interaction.response.edit_message(
            content=f"```bash\n{self.history}```",
            view=Confirm(history=self.history + "\n", hostname=self.hostname),
        )

    async def on_error(self, interaction: discord.Interaction, err: Exception) -> None:
        info = traceback.format_exception(type(err), err, err.__traceback__)
        terminal = f"```bash\n{self.history}Something went wrong:\n\n{''.join(info)}```"

        await interaction.response.edit_message(content=terminal, view=None)


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

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, btn: discord.ui.Button):
        terminal = f"```bash\n{self.history}Interrupt signal received```"

        await interaction.response.edit_message(content=terminal, view=None)
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


client = Client(intents=discord.Intents.all())
client.run(os.getenv("TOKEN"))
