from builtin.quote import parse as quote
from builtin.misc import exit_terminal, clear_terminal

prog_to_parser = {
    # Quotes
    "quote": quote,

    # Misc
    "exit": exit_terminal,
    "clear": clear_terminal,
}
