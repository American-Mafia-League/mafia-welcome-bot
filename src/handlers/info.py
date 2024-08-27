import logging
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import CommandHandler, ContextTypes, filters

from config import settings
from utils import log


def create_handlers() -> list:
    """Creates handlers that process admin's `info` command."""
    return [CommandHandler('info', info)]


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Basic admin info command."""
    log('info')
    log(f'chat id: {update.effective_chat.id}', level=logging.INFO)
    log(f'chat title: {update.effective_chat.title}', level=logging.INFO)
    log(f'chat username: {update.effective_chat.username}', level=logging.INFO)
    log(f'user id: {update.effective_user.id}', level=logging.INFO)
    log(f'user name: {update.effective_user.username}', level=logging.INFO)
    log(f'user full name: {update.effective_user.full_name}', level=logging.INFO)  
    try:
        await update.message.delete()
    except BadRequest as e:
        log(f'cannot delete the "/info" message', level=logging.ERROR)
