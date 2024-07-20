import logging
from telegram.constants import UpdateType
from telegram.ext import Application
from telegram.warnings import PTBUserWarning
from warnings import filterwarnings

from config import settings
from handlers import error
from handlers import debug, info
from handlers import feedback, schedule, welcome
from utils import log


def setup_logging() -> None:
    # Logging
    logging_level = logging.DEBUG if settings.DEBUG else logging.INFO
    logging.basicConfig(filename=settings.LOG_PATH, level=logging_level,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    # Debugging
    filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)


def allowed_updates() -> list:
    """Returns a list of allowed updates."""
    return [UpdateType.MESSAGE, UpdateType.CALLBACK_QUERY, UpdateType.CHAT_MEMBER, UpdateType.CHAT_JOIN_REQUEST]


async def post_init(app: Application) -> None:
    """Initializes bot with data and its tasks."""
    app.bot_data.setdefault('clubs', {})
    app.bot_data.setdefault('players', {})
    app.bot_data.setdefault('schedule', {})
    app.bot_data.setdefault('feedback', {})
    for committee in settings.COMMITTEES:
        app.bot_data['feedback'][committee.id] = {
            'user-messages': {},
            'message-user': {}}


def add_handlers(app: Application) -> None:
    """Adds handlers to the bot."""
    # Error handler.
    app.add_error_handler(error.handler)
    # Debug commands.
    for module in [debug, info]:
        app.add_handlers(module.create_handlers())
    # General chat handling.
    for module in [feedback, schedule, welcome]:
        app.add_handlers(module.create_handlers())