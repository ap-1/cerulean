from typing import override

import discord

from utils.ids import Role
from views.acceptance import AcceptanceModal
from views.finalize import SchoolView


class NameModal(discord.ui.Modal, title="Verification"):
    name: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="What name would you like to go by?",
        style=discord.TextStyle.short,
    )

    @override
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            content="Are you a prospective student (starting Fall '25), a current student (already at CMU), or an alum?",
            view=StudentTypeView(self.name.value),
            ephemeral=True,
        )


class StudentTypeDropdown(discord.ui.Select[discord.ui.View]):
    def __init__(self, name: str, selected_roles: list[Role]):
        self.name: str = name
        self.selected_roles: list[Role] = selected_roles

        options = [
            discord.SelectOption(label="Prospective", value="PROSPECTIVE_STUDENT"),
            discord.SelectOption(label="Current", value="CURRENT_STUDENT"),
            discord.SelectOption(label="Alum", value="ALUM"),
        ]

        super().__init__(
            placeholder="Select the type of student you are",
            min_values=1,
            max_values=1,
            options=options,
        )

    @override
    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        student_type = Role[value]

        self.selected_roles.append(student_type)

        if student_type != Role.PROSPECTIVE_STUDENT:
            return await interaction.response.edit_message(
                content="What school are you in?",
                view=SchoolView(self.name, self.selected_roles),
            )

        await interaction.response.edit_message(
            content="Have you been accepted?",
            view=AcceptanceModal(self.name, self.selected_roles),
        )


class ProgramDropdown(discord.ui.Select[discord.ui.View]):
    def __init__(self, name: str, selected_roles: list[Role]):
        self.name: str = name
        self.selected_roles: list[Role] = selected_roles

        options = [
            discord.SelectOption(label="Undergraduate", value="UNDERGRADUATE"),
            discord.SelectOption(label="Graduate", value="GRAD_STUDENT"),
        ]

        super().__init__(
            placeholder="Select the type of program you are in",
            min_values=1,
            max_values=1,
            options=options,
        )

    @override
    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        program_type = Role[value]

        if program_type != Role.GRAD_STUDENT:
            self.selected_roles.append(program_type)

            return await interaction.response.edit_message(
                content="What school are you in?",
                view=SchoolView(self.name, self.selected_roles),
            )

        await interaction.response.edit_message(
            content="Have you been accepted?",
            view=AcceptanceModal(self.name),
        )


class StudentTypeView(discord.ui.View):
    def __init__(self, name: str):
        super().__init__()
        self.add_item(StudentTypeDropdown(name, []))
