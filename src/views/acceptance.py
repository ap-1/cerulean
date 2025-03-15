import discord

from utils.ids import Role
from views.finalize import SchoolView, verify


class AcceptanceModal(discord.ui.View):
    def __init__(self, name: str, selected_roles: list[Role]):
        super().__init__()
        self.name: str = name
        self.selected_roles: list[Role] = selected_roles

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def yes_button(
        self,
        interaction: discord.Interaction,
        _button: discord.ui.Button[discord.ui.View],
    ):
        await interaction.response.edit_message(
            content="What school are you in?",
            view=SchoolView(self.name, self.selected_roles),
        )

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def no_button(
        self,
        interaction: discord.Interaction,
        _button: discord.ui.Button[discord.ui.View],
    ):
        await verify(interaction, self.name, self.selected_roles, False)
