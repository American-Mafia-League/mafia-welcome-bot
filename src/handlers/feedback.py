from datetime import datetime
from enum import Enum
import logging 
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, MessageOriginUser, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, filters, MessageHandler, TypeHandler

from config import settings
import utils


State = Enum('State', [
    'WAITING_FOR_CHAT',
    'CONVERSATION',
])


def create_handlers() -> list:
    """Creates handlers that process `feedback` command."""
    committee_chats = [committee['id'] for committee in settings.COMMITTEES]
    return [ConversationHandler(
        entry_points=[
            CommandHandler('feedback', feedback, filters.ChatType.PRIVATE),
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.REPLY & filters.Chat(committee_chats),
                           answer_feedback),
        ],
        states={
            State.WAITING_FOR_CHAT: [CallbackQueryHandler(start_conversation)],
            State.CONVERSATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback)],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, timeout)],
        },
        fallbacks=[
            CommandHandler('end', end, filters.ChatType.PRIVATE),
        ],
        allow_reentry=False,
        conversation_timeout=settings.CONVERSATION_TIMEOUT,
        name="feedback",
        persistent=True)]


def committee_to_text(committee_id: int) -> str:
    "Transform committee ID into a word in 2nd case."
    for committee in settings.COMMITTEES:
        if committee.id == committee_id:
            return committee.case
    return None


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    """When user uses the `feedback` command."""
    utils.log('feedback')
    message = 'Выберите нужный комитет:'
    keyboard = [[InlineKeyboardButton(committee.title, callback_data=committee.id)] for committee in settings.COMMITTEES]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_user.send_message(message, reply_markup=reply_markup)
    return State.WAITING_FOR_CHAT


async def start_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    """When user chooses the chat to talk to."""
    utils.log('start_conversation')
    await update.callback_query.answer()
    context.user_data['feedback'] = update.callback_query.data
    message = (
        f'Вы на связи с {committee_to_text(context.user_data['feedback'])}. '
        f'Чтобы завершить сеанс, нажмите /end. '
        f'Сеанс завершится автоматически по истечении суток.')
    await update.callback_query.edit_message_text(message)
    return State.CONVERSATION


async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    """When user sends a message withing the conversation."""
    utils.log('handle_feedback')
    message = await context.bot.forward_message(context.user_data['feedback'], update.effective_chat.id, update.message.id)
    user_messages_dict = context.bot_data['feedback'][context.user_data['feedback']]['user-messages']
    user_messages_dict.setdefault(update.effective_user.id, [])
    user_messages_dict[update.effective_user.id].append(message.id)
    message_user_dict = context.bot_data['feedback'][context.user_data['feedback']]['message-user']
    message_user_dict[message.id] = update.effective_user.id
    return State.CONVERSATION


async def answer_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    """When someone in the chat replies to the feedback."""
    utils.log('answer_feedback')    
    forwarded_feedback = update.message.reply_to_message
    message_user_dict = context.bot_data['feedback'][update.effective_chat.id]['message-user']
    feedback_user_id = message_user_dict.get(forwarded_feedback.id, None)
    if feedback_user_id:
        await context.bot.forward_message(feedback_user_id, update.effective_chat.id, update.message.id)
    return ConversationHandler.END


async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """When the conversation timepout is exceeded."""
    utils.log('timeout')
    user = update.effective_user
    message = (
        f'Общение с {committee_to_text(context.user_data['feedback'])} автоматически завершено. '
        f'Если вы хотите продолжить общение, отправьте снова команду /feedback.')
    await user.send_message(message)
    message = f'Сеанс с {utils.mention(update.effective_user)} был автоматически завершён.'
    await context.bot.send_message(context.user_data['feedback'], message)    
    clear_conversation_history(update, context)
    return ConversationHandler.END


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """When a user ends the conversation."""
    utils.log('end')
    message = f'Общение с {committee_to_text(context.user_data['feedback'])} было завершено.'
    await update.effective_user.send_message(message)
    message = f'{utils.mention(update.effective_user)} завершил сеанс.'
    await context.bot.send_message(context.user_data['feedback'], message)
    clear_conversation_history(update, context)    
    return ConversationHandler.END


def clear_conversation_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """When the conversation is over."""
    utils.log('clear_conversation_history')
    user_messages_dict = context.bot_data['feedback'][context.user_data['feedback']]['user-messages']
    user_messages = user_messages_dict[update.effective_user.id]
    message_user_dict = context.bot_data['feedback'][context.user_data['feedback']]['message-user']
    for message_id in user_messages:
        del message_user_dict[message_id]
    del user_messages_dict[update.effective_user.id]
    context.user_data['feedback'] = None