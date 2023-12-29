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
