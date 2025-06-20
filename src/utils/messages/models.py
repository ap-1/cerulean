import os
from datetime import datetime
from typing import final
from urllib.parse import urlparse

from pony.orm import Database, Optional, PrimaryKey, Required, Set

database_url = os.getenv("DATABASE_URL")
if database_url is None:
    raise ValueError("DATABASE_URL environment variable not set")

result = urlparse(database_url)

user = result.username
password = result.password
host = result.hostname
port = result.port
database = result.path.lstrip("/")

db = Database()
db.bind(
    provider="postgres",
    user=user,
    password=password,
    host=host,
    port=port,
    database=database,
)


@final
class Message(db.Entity):
    message_id = PrimaryKey(int)
    author_id = Required(int)
    is_bot = Required(bool)
    channel_id = Required(int)
    thread_id = Optional(int)
    content = Required(str)
    timestamp = Required(datetime)
    reply_to = Optional(int)
    mentions: Set["Mention"] = Set("Mention")


@final
class Mention(db.Entity):
    mentioned_user_id = Required(int)
    message = Required(Message)


db.generate_mapping(create_tables=True)
