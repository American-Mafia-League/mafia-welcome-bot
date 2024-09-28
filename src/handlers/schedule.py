from datetime import datetime
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, filters

from config import settings
from utils import log


def create_handlers() -> list:
    """Creates handlers that process `schedule` command."""
    return [CommandHandler('schedule', schedule, filters.Chat(settings.CHAT_ID))]


async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """When user uses the `schedule` command."""
    log('schedule')
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
        message = 'Обновляем списки пострадавших после турнира и игры в онлайне 💻🎮'
    elif dow == 2:
        message = 'Да будет Срач!!! 🤬'
    elif dow == 3:
        message = 'Сегодня рабочий день 🏢'
    elif dow == 4:
        message = 'Обсуждаем философские вопросы, в частности, жива или мертва американская мафия? 🤔'
    elif dow == 5:
        message = 'Играем турниры, горим на играх, горим на диванах дома, просто горим 🔥'
    elif dow == 6:
        message = 'Сегодня у нас публичная порка судей и обсуждение допов ⚖️'
    bot_message = await update.message.reply_photo(
        settings.SCHEDULE_IMAGE, caption=message,
        reply_to_message_id=update.message.message_id)
    log(f'schedule: {bot_message.photo[0].file_id}')
    context.bot_data['schedule']['timestamp'] = datetime.now().isoformat()
    context.bot_data['schedule']['message_id'] = bot_message.message_id