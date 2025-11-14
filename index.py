from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "7978466946:AAF4gBpJRY0ZKFHVEE0l0lDUAU_JpVq30h8"

async def gas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает, команда /gas получена!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Бот работает!")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("gas", gas))

print("Bot running...")
app.run_polling()
