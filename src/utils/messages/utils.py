from dataclasses import dataclass
from datetime import datetime
from typing import cast

import discord
from pony.orm import db_session

from utils.messages.models import Mention, Message, Reaction


def render_progress_bar(current: int, total: int, bar_length: int = 20) -> str:
    if total == 0:
        return "[no progress info]"

    percent = current / total
    filled = int(bar_length * percent)
    bar = "█" * filled + "░" * (bar_length - filled)
    return f"[{bar}] {int(percent * 100)}%"


@dataclass
class ReactionData:
    emoji_id: int | None
    emoji_unicode: str | None
    users: list[int]


@dataclass
class MessageData:
    message_id: int
    author_id: int
    is_bot: bool
    channel_id: int
    thread_id: int | None
    content: str
    timestamp: datetime
    reply_to: int | None
    mentioned_ids: list[int]
    reactions: list[ReactionData]


async def index_messages(messages: list[discord.Message]):
    try:
        # run async operations first
        message_data: list[MessageData] = []

        for message in messages:
            # thread + channel logic
            if isinstance(message.channel, discord.Thread):
                thread_id = message.channel.id
                channel_id = message.channel.parent_id
            else:
                thread_id = None
                channel_id = message.channel.id

            reply_id = (
                message.reference.message_id  # type: ignore[possibly-unbound-attribute]
                if message.reference
                else None
            )
            mentioned_ids = [user.id for user in message.mentions]

            # collect reaction data
            reactions_data: list[ReactionData] = []
            for reaction in message.reactions:
                emoji_id = None
                emoji_unicode = None

                if type(reaction.emoji) is str:
                    # unicode emoji
                    emoji_unicode = cast(str, reaction.emoji)  # pyright: ignore[reportUnnecessaryCast]
                else:
                    # custom emoji
                    emoji = cast(discord.PartialEmoji | discord.Emoji, reaction.emoji)
                    emoji_id = emoji.id

                    if emoji_id is None:
                        # deleted custom emoji
                        continue

                # get all users who reacted with this emoji
                reacted_users: list[int] = []
                async for user in reaction.users():
                    reacted_users.append(user.id)

                reactions_data.append(
                    ReactionData(
                        emoji_id=emoji_id,
                        emoji_unicode=emoji_unicode,
                        users=reacted_users,
                    )
                )

            message_data.append(
                MessageData(
                    message_id=message.id,
                    author_id=message.author.id,
                    is_bot=message.author.bot,
                    channel_id=channel_id,
                    thread_id=thread_id,
                    content=message.content,
                    timestamp=message.created_at,
                    reply_to=reply_id,
                    mentioned_ids=mentioned_ids,
                    reactions=reactions_data,
                )
            )

        # do all database operations synchronously
        with db_session:
            for data in message_data:
                if not Message.exists(message_id=data.message_id):
                    print("Creating new Message entry for", data.message_id)
                    db_msg = Message(
                        message_id=data.message_id,
                        author_id=data.author_id,
                        is_bot=data.is_bot,
                        channel_id=data.channel_id,
                        thread_id=data.thread_id,
                        content=data.content,
                        timestamp=data.timestamp,
                        reply_to=data.reply_to,
                    )

                    print("Created Message entry:", db_msg)

                    for uid in data.mentioned_ids:
                        Mention(mentioned_user_id=uid, message=db_msg)

                    print("Added mentions for message", data.message_id)

                    for reaction_data in data.reactions:
                        for user_id in reaction_data.users:
                            if not Reaction.exists(
                                message=db_msg,
                                user_id=user_id,
                                emoji_id=reaction_data.emoji_id,
                                emoji_unicode=reaction_data.emoji_unicode,
                            ):
                                Reaction(
                                    message=db_msg,
                                    user_id=user_id,
                                    emoji_id=reaction_data.emoji_id,
                                    emoji_unicode=reaction_data.emoji_unicode,
                                    timestamp=data.timestamp,
                                )

                    print(f"Added reactions for message {data.message_id}")
    except Exception as e:
        import traceback

        print(f"Error while indexing messages: {e}")
        traceback.print_exc()
        raise
