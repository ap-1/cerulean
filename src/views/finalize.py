from typing import cast, override

import discord

from utils.ids import Role


async def verify(
    interaction: discord.Interaction,
    name: str,
    selected_roles: list[Role],
    accepted: bool,
):
    guild = cast(discord.Guild, interaction.guild)
    channel = cast(discord.TextChannel, interaction.channel)
    member = cast(discord.Member, interaction.user)

    roles = [cast(discord.Role, guild.get_role(role.value)) for role in selected_roles]
    unverified = cast(discord.Role, guild.get_role(Role.UNVERIFIED.value))

    await member.add_roles(*roles)
    await member.remove_roles(unverified)
    await member.edit(nick=name)

    accepted_message = "Congrats on being accepted! 🎉" if accepted else ""
    embed = discord.Embed(
        title="Verification Complete",
        description=f"{interaction.user.mention} ({name}) has been verified. {accepted_message}",
        color=discord.Color.green(),
    )

    if accepted:
        roles_text = "\n".join([role.mention for role in roles])
        embed.add_field(name="Assigned Roles", value=roles_text, inline=False)

    await channel.send(embed=embed)
    await interaction.response.edit_message(content="Verification complete!", view=None)


class SchoolDropdown(discord.ui.Select[discord.ui.View]):
    def __init__(self, name: str, selected_roles: list[Role]):
        self.name: str = name
        self.selected_roles: list[Role] = selected_roles

        options = [
            discord.SelectOption(label="BXA", value="BXA"),
            discord.SelectOption(label="CFA", value="CFA"),
            discord.SelectOption(label="MCS", value="MCS"),
            discord.SelectOption(label="SCS", value="SCS"),
            discord.SelectOption(label="CIT (CoE)", value="CIT"),
            discord.SelectOption(label="Dietrich", value="DIETRICH"),
            discord.SelectOption(label="Tepper", value="TEPPER"),
            discord.SelectOption(label="Heinz", value="HEINZ"),
        ]

        super().__init__(
            placeholder="Select your school(s)...",
            min_values=1,
            max_values=3,
            options=options,
        )

    @override
    async def callback(self, interaction: discord.Interaction):
        for value in self.values:
            if (role := Role[value]) not in self.selected_roles:
                self.selected_roles.append(role)

        await verify(interaction, self.name, self.selected_roles, True)


class SchoolView(discord.ui.View):
    def __init__(self, name: str, selected_roles: list[Role]):
        super().__init__()
        self.add_item(SchoolDropdown(name, selected_roles))
