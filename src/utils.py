from datetime import datetime
from functools import reduce
import logging
from telegram import User

from config import settings


def log(message: str, level=logging.DEBUG) -> None:
    """Logging/debugging helper."""
    logging.getLogger(__name__).log(level, message)
    if settings.DEBUG:
        print(f'⌚️ {datetime.now().strftime(settings.DATETIME_FORMAT)}: {message}')


def user_repr(user: User) -> str:
    """Returns a string representation of a user."""
    return f'{user.id} ({user.full_name}, https://t.me/{getattr(user, "username", user.id)})'


def mention(user: User) -> str:
    """Returns a mention of a user."""
    mention = user.mention_markdown(user.name)
    if user.username:
        mention = f'{user.full_name} ({mention})'
    return mention


def nested_getattr(obj, attr, default=None):
    try:
        return reduce(getattr, attr.split("."), obj)
    except AttributeError:
        return default