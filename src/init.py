import logging
from telegram.constants import UpdateType
from telegram.ext import Application
from telegram.warnings import PTBUserWarning
import re
from warnings import filterwarnings

from config import settings
from handlers import error
from handlers import debug, info
from handlers import schedule, welcome
from utils import log


class HttpxLoggingFilter(logging.Filter):
    def filter(self, record):
        pattern = r'getUpdates "HTTP\/1\.1 200 OK"'
        if re.search(pattern, record.getMessage()):
            return 0
        return 1


def setup_logging() -> None:
    # Logging
    logging_level = logging.DEBUG if settings.DEBUG else logging.INFO
    logging.basicConfig(filename=settings.LOG_PATH, level=logging_level,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('httpx').addFilter(HttpxLoggingFilter())
    # Debugging
    filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)


def allowed_updates() -> list:
    """Returns a list of allowed updates."""
    return [UpdateType.MESSAGE, UpdateType.CALLBACK_QUERY, UpdateType.CHAT_MEMBER, UpdateType.CHAT_JOIN_REQUEST]


async def post_init(app: Application) -> None:
    """Initializes bot with data and its tasks."""
    log('post_init')
    log(app.bot_data)
    app.bot_data.setdefault('clubs', {})
    app.bot_data.setdefault('players', {})
    app.bot_data.setdefault('schedule', {})


def add_handlers(app: Application) -> None:
    """Adds handlers to the bot."""
    # Error handler.
    app.add_error_handler(error.handler)
    # Debug commands.
    for module in [debug, info]:
        app.add_handlers(module.create_handlers())
    # General chat handling.
    for module in [schedule, welcome]:
        app.add_handlers(module.create_handlers())