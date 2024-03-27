from telegram.ext import Application

import utils
from handlers import error
from handlers import debug, info
from handlers import request, welcome


async def post_init(app: Application) -> None:
    """Initializes bot with data and its tasks."""
    utils.log('intializing_players')
    app.bot_data.setdefault('players', {})    


def add_handlers(app: Application) -> None:
    """Adds handlers to the bot."""
    # Error handler.
    app.add_error_handler(error.handler)
    # Debug commands.
    for module in [debug, info]:
        app.add_handlers(module.create_handlers())
    # General chat handling.
    for module in [request, welcome]:
        app.add_handlers(module.create_handlers())