import os
import threading
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from database import init_db, add_task, get_tasks, delete_task, complete_task
from agent import process_message
from scheduler import start_scheduler
from quiz_solver import solve_quiz_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} started the bot")
    await update.message.reply_text(
        "Hello Abdi! I'm your AI assistant bot. Use /help to see what I can do."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "I'm ABDI AI! I can understand natural language.\n\n"
        "Examples:\n"
        "- \"Add task buy groceries\"\n"
        "- \"Show my tasks\"\n"
        "- \"Schedule meeting tomorrow at 3pm\"\n"
        "- \"What events do I have?\"\n"
        "- \"Tell me a joke\"\n"
        "- Send a PDF or photo of a quiz to get it solved\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message"
    )

async def add_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /addtask <task title>")
        return
    title = " ".join(context.args)
    user_id = update.effective_user.id
    task_id = add_task(user_id, title)
    await update.message.reply_text(f"Task added! (ID: {task_id})")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = get_tasks(user_id)
    if not tasks:
        await update.message.reply_text("No tasks found. Add one with /addtask")
        return
    lines = ["Your tasks:"]
    for t in tasks:
        status = "✅" if t["completed"] else "⬜"
        lines.append(f"{status} {t['id']}. {t['title']}")
    await update.message.reply_text("\n".join(lines))

async def done_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /done <task_id>")
        return
    try:
        task_id = int(context.args[0])
        user_id = update.effective_user.id
        if complete_task(task_id, user_id):
            await update.message.reply_text(f"Task {task_id} marked as completed!")
        else:
            await update.message.reply_text("Task not found.")
    except ValueError:
        await update.message.reply_text("Please provide a valid task ID.")

async def delete_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /deletetask <task_id>")
        return
    try:
        task_id = int(context.args[0])
        user_id = update.effective_user.id
        if delete_task(task_id, user_id):
            await update.message.reply_text(f"Task {task_id} deleted!")
        else:
            await update.message.reply_text("Task not found.")
    except ValueError:
        await update.message.reply_text("Please provide a valid task ID.")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        file = update.message.document
        ext = file.file_name.lower()
        if not ext.endswith(".pdf"):
            await update.message.reply_text("Please send a PDF file.")
            return
        file_name = file.file_name
    elif update.message.photo:
        photo = update.message.photo[-1]
        file = photo
        file_name = "quiz_image.jpg"
    else:
        return

    await update.message.reply_text("Got your file! Solving the quiz...")
    file_path = f"/tmp/{file_name}"
    file_obj = await file.get_file()
    await file_obj.download_to_drive(file_path)
    try:
        output_path = await solve_quiz_file(file_path, file_name)
        with open(output_path, "rb") as f:
            await update.message.reply_document(f, caption="Quiz solved! ✅")
        os.remove(output_path)
    except Exception as e:
        await update.message.reply_text(f"Sorry, couldn't solve: {e}")
    os.remove(file_path)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.effective_user.id
    logger.info(f"AI processing from user {user_id}: {user_message}")
    response = await process_message(user_id, user_message)
    await update.message.reply_text(response)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    from http.server import HTTPServer, BaseHTTPRequestHandler
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        def log_message(self, *a):
            pass
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health server running on port {port}")
    server.serve_forever()

def main():
    threading.Thread(target=start_health_server, daemon=True).start()
    init_db()
    app = Application.builder().token(BOT_TOKEN).post_init(start_scheduler).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addtask", add_task_command))
    app.add_handler(CommandHandler("tasks", list_tasks))
    app.add_handler(CommandHandler("done", done_task))
    app.add_handler(CommandHandler("deletetask", delete_task_command))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Bot is starting polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
