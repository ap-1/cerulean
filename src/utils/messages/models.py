import os
from datetime import datetime
from typing import final

from pony.orm import (
    Database,
    Optional,
    PrimaryKey,
    Required,
    Set,
    db_session,
    sql_debug,
)

user = os.getenv("PGUSER")
password = os.getenv("PGPASSWORD")
host = os.getenv("PGHOST")
port = os.getenv("PGPORT")
database = os.getenv("PGDATABASE")

if not all([user, password, host, port, database]):
    raise ValueError(
        "One or more required PostgreSQL environment variables are not set"
    )

db = Database()
db.bind(
    provider="postgres",
    user=user,
    password=password,
    host=host,
    port=port,
    database=database,
)
sql_debug(True)


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
    mentions = Set("Mention")  # pyright: ignore[reportUnknownVariableType]


@final
class Mention(db.Entity):
    mentioned_user_id = Required(int)
    message = Required(Message)


with db_session:
    db.generate_mapping(create_tables=True)
