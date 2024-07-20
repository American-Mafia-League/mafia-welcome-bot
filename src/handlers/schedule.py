from datetime import datetime
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, filters

from config import settings
import utils


def create_handlers() -> list:
    """Creates handlers that process `schedule` command."""
    return [CommandHandler('schedule', schedule, filters.Chat(settings.CHAT_ID))]


async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """When user uses the `schedule` command."""
    utils.log('schedule')
    if 'timestamp' in context.bot_data['schedule']:
        time_past = datetime.now() - datetime.fromisoformat(context.bot_data['schedule']['timestamp'])
        if time_past.total_seconds() < settings.SLOW_MODE:
            await update.message.reply_text(
                'Смотри выше ☝️', reply_to_message_id=context.bot_data['schedule']['message_id'])
            return
    message = ''
    dow = datetime.now().weekday()
    if dow == 0:
        message = 'Сегодня у нас дружеский стёб 🌚'
    elif dow == 1:
        message = 'Обсуждаем игры в инетке'
    elif dow == 2:
        message = 'Да будет Срач!!!'
    elif dow == 3:
        message = 'Рабочий день'
    elif dow == 4:
        message = 'Обсуждение философских вопросов'
    elif dow == 5:
        message = 'Пьём Маргариту и играем в баланс'
    elif dow == 6:
        message = 'Жива или мертва американская мафия?\n\nКто едет в Сакраменто?'
    bot_message = await update.message.reply_photo(
        settings.SCHEDULE_IMAGE, caption=message,
        reply_to_message_id=update.message.message_id)
    context.bot_data['schedule']['timestamp'] = datetime.now().isoformat()
    context.bot_data['schedule']['message_id'] = bot_message.message_id