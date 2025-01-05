import asyncio
import json
from telegram import Update, InputMediaPhoto, InputMediaVideo, InputMediaDocument, Sticker
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import Forbidden

# Default auto delete time in seconds (30 minutes)
OWNER_ID = '7574316340'  # Replace this with the actual owner ID
authorized_users = set()
authorized_user_ids = set()
started_users = set()  # Track users who started the bot
group_ids = set()  # Track groups where the bot is added
global_authorized_users = set()  # Users globally authorized by the owner
group_authorized_users = {}  # Group-specific authorizations
group_settings = {}  # Store auto-delete settings per group

# Update Load and Save Functions
DATA_FILE = "data.json"

# Load data from the JSON file
def load_data():
    try:
        with open(DATA_FILE, "r") as file:
            content = file.read().strip()
            if not content:  # If the file is empty
                print(f"{DATA_FILE} is empty. Creating default data.")
                return {}
            return json.loads(content)  # Try parsing JSON if file is not empty
    except json.JSONDecodeError as e:
        print(f"Error loading JSON: {e}")
        return {}  # Return an empty dictionary in case of error
    except FileNotFoundError:
        print(f"{DATA_FILE} not found, creating a new file.")
        return {}  # Return an empty dictionary if file doesn't exist

# Function to save data to JSON file
def save_data():
    data = {
        "started_users": list(started_users),
        "group_ids": list(group_ids),
        "authorized_users": list(authorized_users),
        "authorized_user_ids": list(authorized_user_ids),
        "global_authorized_users": list(global_authorized_users),
        "group_authorized_users": {k: list(v) for k, v in group_authorized_users.items()},  # Convert sets to lists
        "group_settings": group_settings  # Keep it as a dictionary
    }

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)
# Function to authorize a user and add them to the list
def authorize_user(user_id):
    if user_id not in authorized_user_ids:
        authorized_user_ids.add(user_id)  # Add to set to prevent duplicates
        authorized_users.append(user_id)  # You can also keep the list for other purposes
        print(f"User {user_id} authorized!")
    else:
        print(f"User {user_id} is already authorized.")

# Initialize the data (loading from the file)
data = load_data()
started_users = set(data.get("started_users", []))  # Use a set for uniqueness
group_ids = set(data.get("group_ids", []))
authorized_users = data.get("authorized_users", [])
authorized_user_ids = set(data.get("authorized_user_ids", []))  # Store as set
global_authorized_users = set(data.get("global_authorized_users", []))
group_authorized_users = {k: set(v) for k, v in data.get("group_authorized_users", {}).items()}  # Convert lists to sets
group_settings = data.get("group_settings", {})



# Save data after making changes
save_data()

# Handler to set a timer for auto-delete
async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id

    # Check if the user is an admin or owner
    if not await is_admin_or_owner(user_id, chat_id, context.bot):
        await update.message.reply_text("Only group admins or the owner can set the auto-delete timer.")
        return

    # Ensure a timer value is provided
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /settimer <time_in_minutes> (e.g., /settimer 30)")
        return
    try:
        timer_minutes = int(context.args[0])
        if timer_minutes <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please provide a valid positive integer for the time in minutes.")
        return

    # Set the timer for the group
    group_settings[chat_id] = {"delete_timer": timer_minutes * 60, "auto_delete": True}
    save_data()

    await update.message.reply_text(f"Auto-delete timer set to {timer_minutes} minutes for this group.")

DEFAULT_AUTO_DELETE_TIME = 30 * 60  # Default timer in minutes

async def handle_auto_delete(update, delete_timer):
    """Handle auto-delete logic (simplified for demo)"""
    await asyncio.sleep(delete_timer)
    await update.message.delete()

async def toggle_auto_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global group_settings  # Ensure global variable is used
    chat_id = update.message.chat.id

    # Retrieve or initialize group config with default delete timer
    group_config = group_settings.get(
        chat_id,
        {"delete_timer": DEFAULT_AUTO_DELETE_TIME, "auto_delete": True}
    )

    # Check if the user provided a command argument
    if context.args:
        option = context.args[0].lower()

        # Handle 'on' command
        if option == 'on':
            group_config["auto_delete"] = True
            group_settings[chat_id] = group_config
            save_data()
            auto_delete_status = "enabled"
            await update.message.reply_text(f"Auto-delete is now {auto_delete_status} for this group.")
            return

        # Handle 'off' command
        elif option == 'off':
            group_config["auto_delete"] = False
            group_settings[chat_id] = group_config
            save_data()
            auto_delete_status = "disabled"
            await update.message.reply_text(f"Auto-delete is now {auto_delete_status} for this group.")
            return
        else:
            await update.message.reply_text("Usage: /autodlt <on|off>")
            return
    else:
        # No arguments provided
        await update.message.reply_text("Usage: /autodlt <on|off>")
        return


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
        print(f"New user added: {user_id}")  # Debug line
        save_data()  # Save the data after adding a new user

    if chat_id not in group_ids:
        group_ids.add(chat_id)
        print(f"New group added: {chat_id}")  # Debug line
        save_data()  # Save the data after adding a new group

    await update.message.reply_text(
        " 𝗛𝗲𝗹𝗹𝗼! 𝗜 𝗰𝗮𝗻 𝗵𝗲𝗹𝗽 𝗺𝗮𝗻𝗮𝗴𝗲 𝘆𝗼𝘂𝗿 𝗴𝗿𝗼𝘂𝗽 𝗯𝘆:\n \n "
        "✩ 𝗗𝗲𝗹𝗲𝘁𝗶𝗻𝗴 𝗲𝗱𝗶𝘁𝗲𝗱 𝗺𝗲𝘀𝘀𝗮𝗴𝗲𝘀 ,𝗺𝗲𝗱𝗶𝗮 𝗮𝗻𝗱 𝗮𝗻𝗻𝗼𝘂𝗻𝗰𝗶𝗻𝗴 𝘁𝗵𝗲𝗺.\n\n"
        "✩ 𝗔𝘂𝘁𝗼𝗺𝗮𝘁𝗶𝗰𝗮𝗹𝗹𝘆 𝗱𝗲𝗹𝗲𝘁𝗶𝗻𝗴 𝗺𝗲𝗱𝗶𝗮 𝗮𝗻𝗱 𝘁𝗲𝘅𝘁 𝗺𝗲𝘀𝘀𝗮𝗴𝗲𝘀 𝗮𝗳𝘁𝗲𝗿 𝟯𝟬 𝗺𝗶𝗻𝘂𝘁𝗲𝘀. (𝗗𝗲𝗳𝗮𝘂𝗹𝘁)\n\n "
        "✩ 𝐘𝐨𝐮 𝐂𝐚𝐧 𝐀𝐥𝐬𝐨 𝐌𝐨𝐝𝐢𝐟𝐲 𝐚𝐮𝐭𝐨 𝐝𝐞𝐥𝐞𝐭𝐞 𝐭𝐢𝐦𝐞 𝐢𝐧 𝐲𝐨𝐮𝐫 𝐠𝐫𝐨𝐮𝐩🤩 \n\n  "
        " ~ By using - /settimer X \n"
        "For X= 1  { 1 minute delay }\n"
        "𝙰𝚕𝚜𝚘 𝚝𝚘 𝚍𝚒𝚜𝚊𝚋𝚕𝚎 𝚘𝚛 𝚎𝚗𝚊𝚋𝚕𝚎 𝚙𝚎𝚛𝚖𝚊𝚗𝚎𝚗𝚝𝚕𝚢. \n"
        "Use /autodlt <Off / On>.\n\n"
        "✩ 𝗜𝗴𝗻𝗼𝗿𝗶𝗻𝗴 𝗮𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲𝗱 𝘂𝘀𝗲𝗿𝘀 𝘀𝗽𝗲𝗰𝗶𝗳𝗶𝗲𝗱 𝗯𝘆 𝘁𝗵𝗲 𝗼𝘄𝗻𝗲𝗿 𝗼𝗿 𝗮𝗱𝗺𝗶𝗻𝘀.\n\n"
        " ⋆˙⟡ 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀 (𝗳𝗼𝗿 𝗴𝗿𝗼𝘂𝗽 𝗼𝘄𝗻𝗲𝗿 𝗼𝗿 𝗮𝗱𝗺𝗶𝗻𝘀 𝗼𝗻𝗹𝘆):\n\n"
        "/auth <𝘂𝘀𝗲𝗿𝗶𝗱> 𝐨𝐫 𝐛𝐲 𝐫𝐞𝐩𝐥𝐲𝐢𝐧𝐠 𝐮𝐬𝐞𝐫 𝐭𝐞𝐱𝐭- 𝗔𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲 𝗮 𝘂𝘀𝗲𝗿.\n\n"
        "/unauth <𝘂𝘀𝗲𝗿𝗶𝗱> 𝐨𝐫 𝐛𝐲 𝐫𝐞𝐩𝐥𝐲𝐢𝐧𝐠 𝐮𝐬𝐞𝐫 𝐭𝐞𝐱𝐭- 𝗨𝗻𝗮𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲 𝗮 𝘂𝘀𝗲𝗿.\n\n"
        " ✮ 𝗙𝗼𝗿 𝗮𝗻𝘆 𝗾𝘂𝗲𝗿𝗶𝗲𝘀 𝗮𝗻𝗱 𝗵𝗲𝗹𝗽 - @ImThanos_bot💀 \n"
        "✮ 𝗝𝗼𝗶𝗻 𝗳𝗼𝗿 𝘂𝗽𝗱𝗮𝘁𝗲𝘀 - @copyrightprotection"
    )

async def authorize_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id

    # Check if the user is authorized to perform this action
    if not await is_admin_or_owner(user_id, chat_id, context.bot):
        await update.message.reply_text("Only the group owner or admins can authorize users.")
        return

    # Check if the command is used with a user_id
    if context.args:
        target_user_id = int(context.args[0])  # Extract user_id from the command argument
        target_username = None  # No username available when using user_id directly
    elif update.message.reply_to_message:
        # User is replying to a message
        target_user_id = update.message.reply_to_message.from_user.id
        target_username = update.message.reply_to_message.from_user.username
    else:
        await update.message.reply_text("Usage: Please provide a user ID with /auth <user_id> or reply to a user's message.")
        return

    # Add to global or group-specific authorization
    if user_id == int(OWNER_ID):  # Owner's authorization is global
        global_authorized_users.add(target_user_id)
        await update.message.reply_text(f"User {target_username or target_user_id} has been globally authorized.")
    else:  # Admin's authorization is group-specific
        group_authorized_users.setdefault(chat_id, set()).add(target_user_id)
        await update.message.reply_text(f"User {target_username or target_user_id} has been authorized in this group.")

    save_data()

async def unauthorize_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id

    # Only the owner can unauthorize users globally
    if user_id != int(OWNER_ID):
        await update.message.reply_text("Only the bot owner can unauthorize users globally.")
        return

    # Check if the command is used with a user_id
    if context.args:
        try:
            target_user_id = int(context.args[0])  # Extract user_id from the command argument
            target_username = None  # No username available when using user_id directly
        except ValueError:
            await update.message.reply_text("Invalid user ID. Please provide a valid numeric user ID.")
            return
    elif update.message.reply_to_message:
        # User is replying to a message
        target_user_id = update.message.reply_to_message.from_user.id
        target_username = update.message.reply_to_message.from_user.username
    else:
        await update.message.reply_text("Usage: Please provide a user ID with /unauth <user_id> or reply to a user's message.")
        return

    # Debugging: check user ID being processed
    print(f"Attempting to unauthorize user: {target_user_id}")

    # Remove from global authorized list
    if target_user_id in global_authorized_users:
        global_authorized_users.discard(target_user_id)
        await update.message.reply_text(
            f"User {target_username or target_user_id} has been globally unauthorized."
        )
    else:
        await update.message.reply_text(f"User {target_username or target_user_id} was not authorized globally.")

    # Save data after modification
    save_data()

async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != int(OWNER_ID):
        await update.message.reply_text("Only the bot owner can use this command.")
        return

    # Initialize the count of valid groups
    valid_group_count = 0

    # Loop through all group IDs
    for group_id in group_ids:
        try:
            # Try to get the group chat information
            chat = await context.bot.get_chat(group_id)

            # Count the group only if its title is not None or empty
            if chat.title:
                valid_group_count += 1
        except Exception as e:
            # Skip any group where fetching details failed (no valid group)
            continue

    if valid_group_count > 0:
        await update.message.reply_text(f"The bot is added to {valid_group_count} valid groups.")
    else:
        await update.message.reply_text("The bot is not added to any valid groups.")


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

    recipients = list(started_users | group_ids)
    success_count = 0
    failure_count = 0

    try:
        # Check the type of the message to be broadcasted
        if update.message.reply_to_message.sticker:
            media = update.message.reply_to_message.sticker.file_id
            for recipient in recipients:
                try:
                    await context.bot.send_sticker(chat_id=recipient, sticker=media)
                    success_count += 1
                except Exception as e:
                    print(f"Failed to send to {recipient}: {e}")
                    failure_count += 1
        elif update.message.reply_to_message.photo:
            media = update.message.reply_to_message.photo[-1].file_id
            for recipient in recipients:
                try:
                    await context.bot.send_photo(chat_id=recipient, photo=media)
                    success_count += 1
                except Exception as e:
                    print(f"Failed to send to {recipient}: {e}")
                    failure_count += 1
        elif update.message.reply_to_message.video:
            media = update.message.reply_to_message.video.file_id
            for recipient in recipients:
                try:
                    await context.bot.send_video(chat_id=recipient, video=media)
                    success_count += 1
                except Exception as e:
                    print(f"Failed to send to {recipient}: {e}")
                    failure_count += 1
        elif update.message.reply_to_message.document:
            media = update.message.reply_to_message.document.file_id
            for recipient in recipients:
                try:
                    await context.bot.send_document(chat_id=recipient, document=media)
                    success_count += 1
                except Exception as e:
                    print(f"Failed to send to {recipient}: {e}")
                    failure_count += 1
        elif update.message.reply_to_message.text:
            media = update.message.reply_to_message.text
            for recipient in recipients:
                try:
                    await context.bot.send_message(chat_id=recipient, text=media)
                    success_count += 1
                except Exception as e:
                    print(f"Failed to send to {recipient}: {e}")
                    failure_count += 1
        else:
            await update.message.reply_text("Unsupported media type for broadcasting.")
            return

        # Send broadcast completion summary
        await update.message.reply_text(
            f"Broadcast completed.\n\n"
            f"✅ Successfully sent to: {success_count}\n"
            f"❌ Failed to send to: {failure_count}"
        )

    except Exception as e:
        await update.message.reply_text(f"An error occurred during broadcast: {e}")


async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.edited_message.from_user
    chat_id = update.edited_message.chat.id
    user_id = user.id

    # Skip globally authorized users
    if user_id in global_authorized_users:
        return

    # Skip group-specific authorized users for this chat
    if chat_id in group_authorized_users and user_id in group_authorized_users[chat_id]:
        return

    try:
        username = user.mention_html()
        announcement = f" 𝘙𝘰𝘴𝘦𝘴 𝘢𝘳𝘦 𝘳𝘦𝘥, 𝘷𝘪𝘰𝘭𝘦𝘵𝘴 𝘢𝘳𝘦 𝘣𝘭𝘶𝘦, {username} 𝘦𝘥𝘪𝘵𝘦𝘥 𝘢 𝘮𝘦𝘴𝘴𝘢𝘨𝘦, 𝘯𝘰𝘸 𝘪𝘵'𝘴 𝘨𝘰𝘯𝘦 𝘛𝘰𝘰!😮‍💨"

        # Send announcement about edited message
        await context.bot.send_message(chat_id=chat_id, text=announcement, parse_mode="HTML")

        # Delete the edited message
        await update.edited_message.delete()
    except Exception as e:
        print(f"Failed to delete edited message: {e}")


async def handle_new_message(update, context):
    try:
        # Extract chat ID and message ID safely
        if update.effective_chat and update.message:
            chat_id = update.effective_chat.id
            message_id = update.message.message_id
        else:
            print("Error: update.effective_chat or update.message is None.")
            return  # Exit early if data is missing

        # Get group settings or use defaults
        group_config = group_settings.get(chat_id, {"delete_timer": DEFAULT_AUTO_DELETE_TIME, "auto_delete": True})


        # Check if auto-delete is enabled
        if group_config.get("auto_delete"):
            delete_timer = group_config.get("delete_timer", DEFAULT_AUTO_DELETE_TIME)

            # Schedule the message deletion task
            asyncio.create_task(delete_message(context, chat_id, message_id, delete_timer))
        else:
            print("Auto-delete is disabled for this group.")

    except Exception as e:
        print(f"Error in handle_new_message: {e}")
async def delete_message(context, chat_id, message_id, delete_timer):
    try:

        await asyncio.sleep(delete_timer)  # Wait before deleting

        # Attempt to delete the message
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)


    except Exception as e:
        print(f"Error deleting message {message_id} in chat {chat_id}: {e}")



async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id

    # Check if the user is an admin or owner
    if not await is_admin_or_owner(user_id, chat_id, context.bot):
        await update.message.reply_text("Only group admins or the owner can set the auto-delete timer.")
        return

    # Ensure a timer value is provided
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /settimer <time_in_minutes> (e.g., /settimer 30)")
        return

    try:
        timer_minutes = int(context.args[0])
        if timer_minutes <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please provide a valid positive integer for the time in minutes.")
        return

    # Set the timer for the group
    group_settings[chat_id] = {"delete_timer": timer_minutes * 60, "auto_delete": True}
    save_data()

    await update.message.reply_text(f"Auto-delete timer set to {timer_minutes} minutes for this group.")

# Function to handle being added to a group
async def new_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat.type in ['group', 'supergroup']:
        try:
            await context.bot.send_message(chat_id=chat.id, text=" 𝗛𝗲𝘆! 𝗧𝗵𝗮𝗻𝗸𝘀 𝗙𝗼𝗿 𝗮𝗱𝗱𝗶𝗻𝗴 𝗺𝗲 𝘁𝗼 𝘆𝗼𝘂𝗿 𝗴𝗿𝗼𝘂𝗽 𝗰𝗹𝗶𝗰𝗸 - /start 𝗧𝗼 𝗲𝗻𝗮𝗯𝗹𝗲 𝗺𝘆 𝗳𝘂𝗻𝗰𝘁𝗶𝗼𝗻𝘀 🙃 ")
        except Forbidden:
            print(f"Cannot send message to chat {chat.id}. The bot might have been removed or lacks permissions.")

def main():
    application = ApplicationBuilder().token("7738387262:AAFlJILd8J2BupXtBGBhSOYpKr3Uf5diP-s").build()

    # Adding CommandHandlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("auth", authorize_user))
    application.add_handler(CommandHandler("unauth", unauthorize_user))
    application.add_handler(CommandHandler("listgroup", list_groups))
    application.add_handler(CommandHandler("countuser", count_users))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("settimer", set_timer))
    application.add_handler(CommandHandler("autodlt", toggle_auto_delete))

    # Handling new chat members
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_member))

    # Handling new messages (excluding edited messages)
    application.add_handler(MessageHandler(filters.ALL & ~filters.UpdateType.EDITED_MESSAGE, handle_new_message))

    # Handling edited messages
    application.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_message))

    # Handling message deletion
    application.add_handler(MessageHandler(filters.ALL & ~filters.UpdateType.EDITED_MESSAGE, delete_message))

    # Add auto delete handler for messages
    application.add_handler(MessageHandler(filters.ALL, handle_auto_delete))  # Auto delete handler added here

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()

