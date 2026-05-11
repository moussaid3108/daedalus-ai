import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# CONFIGURATION
DEEPSEEK_KEY = "sk-462e17eb90454973a6aaea3c08e04309"
TELEGRAM_TOKEN ="8731720208:AAEi2jwKy5v3aNOh6D4qy9wMmR7ADYEL6wM"

client = openai.OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
history = [{"role": "system", "content": "Tu es Daedalus, l'assistant Telegram."}]

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    history.append({"role": "user", "content": user_msg})
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=history[-10:]
        )
        answer = response.choices[0].message.content
        await update.message.reply_text(answer)
        history.append({"role": "assistant", "content": answer})
    except Exception as e:
        await update.message.reply_text(f"Erreur : {e}")

if __name__ == "__main__":
    print("🚀 Daedalus Telegram est en ligne !")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat))
    app.run_polling()

