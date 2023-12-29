import argparse

parser = argparse.ArgumentParser(
    prog="save",
    description="quote a specific message by a user",
)
parser.add_argument(
    "-m",
    "--message",
    help="the id of the message to quote",
    dest="message_id",
    required=True,
    type=int,
)

def parse(args: list[str]):
    result = parser.parse_args(args)

    return str(result)
