from datetime import datetime
from enum import Enum
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatMemberStatus
from telegram.ext import CallbackContext, CallbackQueryHandler, ChatJoinRequestHandler, ChatMemberHandler, CommandHandler, ContextTypes, ConversationHandler, filters, MessageHandler, TypeHandler
from telegram.error import Forbidden, TelegramError
from config import settings
import utils


Action = Enum('Action', [
    # Button action:
    'SKIP',
    'MR',
    'MS'
])


State = Enum('State', [
    # Particular states:
    'WAITING_FOR_NICKNAME',
    'WAITING_FOR_TITLE',
    'WAITING_FOR_CITY',
    'WAITING_FOR_CLUB',
    'WAITING_FOR_EXPERIENCE'
])


UserStatus = Enum('UserStatus', [
    # User statuses:
    'OTHER',
    'NEW_MEMBER',
])


def create_handlers() -> list:
    """Creates handlers that process join requests."""
    return [ConversationHandler(
        entry_points=[
            ChatMemberHandler(chat_member_status_changed, chat_member_types=ChatMemberHandler.CHAT_MEMBER),
            MessageHandler(filters.Chat(settings.CHAT_ID) & filters.StatusUpdate.NEW_CHAT_MEMBERS, join),
            MessageHandler(filters.Chat(settings.CHAT_ID) & filters.StatusUpdate.LEFT_CHAT_MEMBER, left),
            ChatJoinRequestHandler(join_request, chat_id=settings.CHAT_ID),
            CommandHandler('join', join_request, ~filters.Chat(settings.CHAT_ID)),
        ],
        states={
            State.WAITING_FOR_NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_nickname)],
            State.WAITING_FOR_TITLE: [CallbackQueryHandler(set_title)],
            State.WAITING_FOR_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_city)],
            State.WAITING_FOR_CLUB: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_club)],
            State.WAITING_FOR_EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_experience)],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, timeout)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel, ~filters.Chat(settings.CHAT_ID)),
        ],
        allow_reentry=True,
        conversation_timeout=settings.CONVERSATION_TIMEOUT,
        name="welcome",
        per_chat=False,
        persistent=True)]


def user_status(update: Update) -> UserStatus:
    """Returns the user status."""
    if not update.chat_member:
        return UserStatus.OTHER
    if update.chat_member.old_chat_member.status and update.chat_member.old_chat_member.status != ChatMemberStatus.LEFT:
        return UserStatus.OTHER
    if update.chat_member.new_chat_member.status == ChatMemberStatus.MEMBER:
        return UserStatus.NEW_MEMBER
    return UserStatus.OTHER


async def chat_member_status_changed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    """When a chat member's status is changed."""
    utils.log('chat_member_status_changed')
    user = update.chat_member.new_chat_member.user
    old_status = utils.nested_getattr(update, 'chat_member.old_chat_member.status')
    new_status = utils.nested_getattr(update, 'chat_member.new_chat_member.status')
    utils.log(f'{utils.user_repr(user)} changed status from "{old_status}" to "{new_status}"', logging.INFO)
    return ConversationHandler.END


async def left(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    """When a user leaves the chat."""
    utils.log('left')
    if update.message.from_user != update.message.left_chat_member:
        await update.message.delete()
    return ConversationHandler.END


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    """When a user joins the chat (by message)."""
    utils.log('join')
    questionnaire_initiated = False
    for user in update.message.new_chat_members:
        utils.log(f'{utils.user_repr(user)} joined the chat', logging.INFO)
        if user.is_bot:
            utils.log(f'new user is a bot')
            continue
        if user.id not in context.bot_data['players'] or not context.bot_data['players'][user.id]['answered']:
            await update.message.delete()
            try:
                await initiate_questionnaire(update, context)
                utils.log(f'{utils.user_repr(user)} is given the questionnaire', logging.INFO)
                questionnaire_initiated = True
            except Forbidden as e:
                message = f'{utils.mention(user)} is trying to join the AML chat, but the bot cannot send messages to them.'
                await context.bot.send_message(settings.ADMIN_CHAT_ID, message)
                utils.log(f'{utils.user_repr(user)} cannot receive the bot\'s messages ({e})', logging.ERROR)
            await context.bot.ban_chat_member(update.message.chat.id, user.id)
            await context.bot.unban_chat_member(update.message.chat.id, user.id)
            utils.log(f'{utils.user_repr(user)} is kicked', logging.INFO)
            continue
        titled_mention = context.bot_data['players'][user.id]['nickname']
        title = context.bot_data['players'][user.id]['title']
        if title:
            titled_mention = title + ' ' + titled_mention
        if context.bot_data['players'][user.id]['introduced']:
            utils.log(f'{utils.user_repr(user)} already introduced themselves', logging.INFO)
            message = (
                'Вы только посмотрите, кто к нам вернулся! Аплодисменты!\n\n'
                f'Встречайте – {titled_mention} ({user.mention_markdown()})!')
            await context.bot.sendMessage(
                chat_id=update.message.chat.id, text=message,
                reply_to_message_id=update.message.id)
            continue
        message = (
            "В нашей большой семье AML пополнение!\n\n"
            f"Встречайте – {titled_mention} ({user.mention_markdown()})!\n\n"
            f"*Город:* {context.bot_data['players'][user.id]['city']}\n"
            f"*Клуб:* {context.bot_data['players'][user.id]['club']}\n"
            f"*Стаж:* {context.bot_data['players'][user.id]['experience']}\n\n"
            "_#about_")
        await context.bot.sendMessage(
            chat_id=update.message.chat.id, text=message,
            reply_to_message_id=update.message.id)
        context.bot_data['players'][user.id]['introduced'] = True
    if questionnaire_initiated:
        return State.WAITING_FOR_NICKNAME
    return ConversationHandler.END


async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    """When a join request is sent."""
    utils.log('join_request')
    user = update.effective_user
    utils.log(f'{utils.user_repr(user)} requested to join the chat', logging.INFO)
    if user.id in context.bot_data['players'] and context.bot_data['players'][user.id]['answered']:
        try:
            await user.approve_join_request(settings.CHAT_ID)
            utils.log(f'{utils.user_repr(user)} already answered the questionnaire, the request is approved', logging.INFO)
        except TelegramError as e:
            utils.log(f'No join requests found: {e}')
        return ConversationHandler.END
    return await initiate_questionnaire(update, context)


async def initiate_questionnaire(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    """Initiates the questionnaire."""
    utils.log('initiate_questionnaire')
    user = update.effective_user
    context.bot_data['players'].setdefault(user.id, {'first_join_timestamp': datetime.now().isoformat()})
    context.bot_data['players'][user.id]['answered'] = False
    context.bot_data['players'][user.id]['introduced'] = False
    message = (f'Доброе утро, {user.full_name}! American Mafia League приветствует вас! '
        'Подписывайтесь на наш канал, чтобы следить за событиями в AML.\n\n'
        'Чтобы попасть в наш чат, вам придётся заполнить небольшую анкету.\n\n'
        'Начнём с самого важного: ваш игровой ник?')
    channel = await context.bot.get_chat(settings.CHANNEL_USERNAME)
    keyboard = [[InlineKeyboardButton(text='Подписаться на канал', url=channel.link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await user.send_message(message, reply_markup=reply_markup)
    return State.WAITING_FOR_NICKNAME


async def set_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    """When the nickname is submitted."""
    utils.log('set_nickname')
    nickname = update.message.text
    context.bot_data['players'][update.effective_user.id]['nickname'] = nickname
    message = (f'Какое обращение вы предпочитаете?')
    keyboard = [
        [
            InlineKeyboardButton("Г-н", callback_data=Action.MR.name),
            InlineKeyboardButton("Г-жа", callback_data=Action.MS.name),
        ],
        [
            InlineKeyboardButton("Пропустить", callback_data=Action.SKIP.name)
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_user.send_message(message, reply_markup=reply_markup)
    return State.WAITING_FOR_TITLE


async def set_title(update: Update, context: CallbackContext) -> State:
    """When the title is submitted."""
    utils.log('set_title')
    await update.callback_query.answer()
    if update.callback_query.data == Action.MR.name:
        context.bot_data['players'][update.effective_user.id]['title'] = 'г-н'
    elif update.callback_query.data == Action.MS.name:
        context.bot_data['players'][update.effective_user.id]['title'] = 'г-жа'
    else:
        context.bot_data['players'][update.effective_user.id]['title'] = None
    message = (f'В каком городе вы проживаете?')
    await update.callback_query.edit_message_text(message)
    return State.WAITING_FOR_CITY


async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    """When the city is submitted."""
    utils.log('set_city')
    context.bot_data['players'][update.effective_user.id]['city'] = update.message.text
    message = (f'В каком клубе вы играете?')
    await update.effective_user.send_message(message)
    return State.WAITING_FOR_CLUB


async def set_club(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    """When the club is submitted."""
    utils.log('set_club')
    context.bot_data['players'][update.effective_user.id]['club'] = update.message.text
    message = (f'Как давно вы играете в спортивную мафию?')
    await update.effective_user.send_message(message)
    return State.WAITING_FOR_EXPERIENCE


async def set_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """When the experience is submitted."""
    utils.log('set_experience')
    user = update.effective_user
    context.bot_data['players'][user.id]['experience'] = update.message.text
    context.bot_data['players'][user.id]['answered'] = True
    try:
        await user.approve_join_request(settings.CHAT_ID)
        utils.log(f'{utils.user_repr(user)} just finished the questionnaire, the request is approved', logging.INFO)
    except TelegramError as e:
        utils.log(f'No join requests found: {e}')
    message = (f'Спасибо за анкету! Теперь вы можете пользоваться нашим чатом.')
    keyboard = [[InlineKeyboardButton(text='Перейти к чату', url=settings.CHAT_INVITE_LINK)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await user.send_message(message, reply_markup=reply_markup)
    return ConversationHandler.END


async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """When the conversation timepout is exceeded."""
    utils.log('timeout')
    user = update.effective_user
    message = (
        'Уже прошли сутки, а вы всё ещё не заполнили анкету. '
        'Мы отклоняем вашу заявку, но вы всегда можете податься '
        'снова, нажав /join.')
    await user.send_message(message)
    await user.decline_join_request(settings.CHAT_ID)
    utils.log(f'{utils.user_repr(user)} timed out, the request is declined', logging.INFO)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """When a user cancels the process."""
    utils.log('cancel')
    message = 'Вы можете заполнить анкету снова, нажав /join.'
    await update.effective_user.send_message(message)
    if update.chat_join_request:
        await update.chat_join_request.from_user.decline_join_request(
            update.chat_join_request.chat.id)
    return ConversationHandler.END
