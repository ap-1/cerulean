import discord
from pony.orm import db_session

from utils.messages.models import Mention, Message


def render_progress_bar(current: int, total: int, bar_length: int = 20) -> str:
    if total == 0:
        return "[no progress info]"

    percent = current / total
    filled = int(bar_length * percent)
    bar = "█" * filled + "░" * (bar_length - filled)
    return f"[{bar}] {int(percent * 100)}%"


@db_session
def index_message_sync(message: discord.Message):
    # thread + channel logic
    if isinstance(message.channel, discord.Thread):
        thread_id = message.channel.id
        channel_id = message.channel.parent_id
    else:
        thread_id = None
        channel_id = message.channel.id

    print("About to access message attributes")

    reply_id = (
        message.reference.message_id  # ty: ignore[possibly-unbound-attribute]
        if message.reference
        else None
    )
    mentioned_ids = [user.id for user in message.mentions]

    print("About to run DB query")

    if not Message.exists(message_id=message.id):
        print("Creating new Message entry for", message.id)
        db_msg = Message(
            message_id=message.id,
            author_id=message.author.id,
            is_bot=message.author.bot,
            channel_id=channel_id,
            thread_id=thread_id,
            content=message.content,
            timestamp=message.created_at,
            reply_to=reply_id,
        )

        print("Created Message entry:", db_msg)
        for uid in mentioned_ids:
            Mention(mentioned_user_id=uid, message=db_msg)

        print("Added mentions for message", message.id)
