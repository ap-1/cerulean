import argparse

parser = argparse.ArgumentParser(
    prog="query",
    description="query a random quote from a specific user"
)
parser.add_argument(
    "-u",
    "--user",
    help="the user id to query against",
    dest="user_id",
    required=True,
    type=int,
)

def parse(args: list[str]):
    result = parser.parse_args(args)

    return str(result)
