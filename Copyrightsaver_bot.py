import asyncio
from telegram import Update, InputMediaPhoto, InputMediaVideo, InputMediaDocument, Sticker
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

OWNER_ID = '7574316340'  # Replace this with the actual owner ID
authorized_users = set()
authorized_user_ids = set()
started_users = set()  # Track users who started the bot
group_ids = set()  # Track groups where the bot is added

async def bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_ids.add(update.my_chat_member.chat.id)
    group_owner = update.my_chat_member.from_user.username
    await context.bot.send_message(
        chat_id=update.my_chat_member.chat.id,
        text=f"Hello! I was added by @{group_owner}.\n"
             "/start me first\n"
             "I will manage this group by:\n"
             "- Deleting edited messages and announcing them.\n"
             "- Automatically deleting media and text messages after 30 minutes.\n"
             "- Ignoring authorized users specified by the group owner or admins.\n\n"
             "Commands (for owner or admins only):\n"
             "/auth <username_or_userid> - Authorize a user.\n"
             "/unauth <username_or_userid> - Unauthorize a user.\n"
             "For any queries and help - @imthanos_bot\n"
             "Join for updates - @copyrightprotection"
    )

async def is_admin_or_owner(user_id, chat_id, bot):
    if user_id == int(OWNER_ID):
        return True
    chat_admins = await bot.get_chat_administrators(chat_id)
    return any(admin.user.id == user_id for admin in chat_admins)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    if user_id not in started_users:
        started_users.add(user_id)
    if chat_id not in group_ids:
        group_ids.add(chat_id)

    await update.message.reply_text(
        "Hello! I can help manage your group by:\n"
        "- Deleting edited messages and announcing them.\n"
        "- Automatically deleting media and text messages after 30 minutes.\n"
        "- Ignoring authorized users specified by the owner or admins.\n"
        "Commands (for group owner or admins only):\n"
        "/auth <username_or_userid> - Authorize a user.\n"
        "/unauth <username_or_userid> - Unauthorize a user.\n"
        "For any queries and help - @imthanos_bot\n"
        "Join for updates - @copyrightprotection"
    )

async def authorize_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    if not await is_admin_or_owner(user_id, chat_id, context.bot):
        await update.message.reply_text("Only the group owner or admins can authorize users.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /auth <username_or_userid>")
        return
    identifier = context.args[0].lstrip("@")
    if identifier.isdigit():
        authorized_user_ids.add(int(identifier))
        await update.message.reply_text(f"User ID {identifier} has been authorized. I will now ignore this user.")
    else:
        authorized_users.add(identifier)
        await update.message.reply_text(f"User @{identifier} has been authorized. I will now ignore this user.")

async def unauthorize_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    if not await is_admin_or_owner(user_id, chat_id, context.bot):
        await update.message.reply_text("Only the group owner or admins can unauthorize users.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /unauth <username_or_userid>")
        return
    identifier = context.args[0].lstrip("@")
    if identifier.isdigit():
        if int(identifier) in authorized_user_ids:
            authorized_user_ids.remove(int(identifier))
            await update.message.reply_text(f"User ID {identifier} has been unauthorized.")
        else:
            await update.message.reply_text(f"User ID {identifier} is not in the authorization list.")
    else:
        if identifier in authorized_users:
            authorized_users.remove(identifier)
            await update.message.reply_text(f"User @{identifier} has been unauthorized.")
        else:
            await update.message.reply_text(f"User @{identifier} is not in the authorization list.")

async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != int(OWNER_ID):
        await update.message.reply_text("Only the bot owner can use this command.")
        return

    group_list = []
    for group_id in group_ids:
        try:
            chat = await context.bot.get_chat(group_id)
            group_list.append(f"{chat.title} (ID: {group_id})")
        except Exception as e:
            group_list.append(f"Unknown Group (ID: {group_id}) - Error: {e}")

    if group_list:
        await update.message.reply_text("Groups where bot is added:\n" + "\n".join(group_list))
    else:
        await update.message.reply_text("The bot is not added to any groups yet.")

async def count_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != int(OWNER_ID):
        await update.message.reply_text("Only the bot owner can use this command.")
        return

    total_users = len(started_users)
    await update.message.reply_text(f"Total number of users who started the bot: {total_users}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != int(OWNER_ID):
        await update.message.reply_text("Only the bot owner can use this command.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a message to broadcast it.")
        return

    media = None
    if update.message.reply_to_message.photo:
        media = InputMediaPhoto(update.message.reply_to_message.photo[-1].file_id)
    elif update.message.reply_to_message.video:
        media = InputMediaVideo(update.message.reply_to_message.video.file_id)
    elif update.message.reply_to_message.sticker:
        media = update.message.reply_to_message.sticker.file_id
    elif update.message.reply_to_message.document:
        media = InputMediaDocument(update.message.reply_to_message.document.file_id)
    else:
        media = update.message.reply_to_message.text

    recipients = list(started_users | group_ids)
    success_count = 0
    failure_count = 0

    for recipient in recipients:
        try:
            if isinstance(media, str):
                await context.bot.send_message(chat_id=recipient, text=media)
            elif isinstance(media, Sticker):
                await context.bot.send_sticker(chat_id=recipient, sticker=media)
            else:
                await context.bot.send_media_group(chat_id=recipient, media=[media])
            success_count += 1
        except Exception as e:
            print(f"Failed to send to {recipient}: {e}")
            failure_count += 1

    await update.message.reply_text(f"Broadcast completed.\n\n"
                                    f"✅ Successfully sent to: {success_count}\n"
                                    f"❌ Failed to send to: {failure_count}")

async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.edited_message.from_user
    if user.username in authorized_users or user.id in authorized_user_ids:
        return
    try:
        username = user.mention_html()
        chat_id = update.edited_message.chat.id
        announcement = f"{username} edited a message. I deleted it! 🤡"
        await context.bot.send_message(chat_id=chat_id, text=announcement, parse_mode="HTML")
        await update.edited_message.delete()
    except Exception as e:
        print(f"Failed to delete edited message: {e}")

async def handle_new_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.username in authorized_users or user.id in authorized_user_ids:
        return
    chat_id = update.message.chat.id
    message_id = update.message.message_id

    asyncio.create_task(delete_message(context, chat_id, message_id))

async def delete_message(context, chat_id, message_id):
    await asyncio.sleep(1800)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Failed to delete message {message_id} from chat {chat_id}: {e}")

def main():
    application = ApplicationBuilder().token("8163953947:AAF19ociC09949555FNrmSq5CuVeK6D3A6E").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("auth", authorize_user))
    application.add_handler(CommandHandler("unauth", unauthorize_user))
    application.add_handler(CommandHandler("listgroup", list_groups))
    application.add_handler(CommandHandler("countuser", count_users))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_message))
    application.add_handler(MessageHandler(filters.ALL & ~filters.UpdateType.EDITED_MESSAGE, handle_new_message))

    application.run_polling()

if __name__ == "__main__":
    main()



