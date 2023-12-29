import discord
import typing

if typing.TYPE_CHECKING:
    from main import Terminal


async def exit_terminal(
    args: list[str], modal: "Terminal", interaction: discord.Interaction
):
    terminal = f"```bash\n{modal.history}Interrupt signal received```"

    await interaction.response.edit_message(content=terminal, view=None)
    modal.stop()


async def clear_terminal(
    args: list[str], modal: "Terminal", interaction: discord.Interaction
):
    modal.history = f"{interaction.user.display_name}@{modal.hostname}:~$ "
    modal.cleared = True
