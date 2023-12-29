import argparse
import discord
import typing

if typing.TYPE_CHECKING:
    from main import Terminal

parser = argparse.ArgumentParser(
    prog="quote", description="query a random quote from a specific user"
)
parser.add_argument(
    "-u",
    "--user",
    help="the user id to query against",
    dest="user_id",
    required=True,
    type=int,
)


async def parse(args: list[str], modal: "Terminal", interaction: discord.Interaction):
    result = parser.parse_args(args)

    return str(result)

async def quote_reaction_handler(client: discord.Client, payload: discord.RawReactionActionEvent):
    channel = client.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    if message.author == client.user:
        return

    await message.reply(
        mention_author=False,
        content=f'"{message.content}" - {message.author.display_name}\nQuoted by {payload.member.display_name}',
        allowed_mentions=discord.AllowedMentions.none(),
    )

