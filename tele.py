import os
import subprocess
import telebot
from openai import OpenAI

# Les variables sont gérées par Coolify
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Mémoire système pour l'IA
history = [{"role": "system", "content": "Tu es Daedalus, l'agent personnel de Kam. Tu peux exécuter des commandes via /exec."}]

def execute_terminal(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout if result.stdout else result.stderr
    except Exception as e:
        return str(e)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_input = message.text
    
    # Commande directe
    if user_input.startswith('/exec '):
        cmd = user_input.split('/exec ')[1]
        output = execute_terminal(cmd)
        bot.reply_to(message, f"```\n{output}\n```", parse_mode="Markdown")
        return

    # Mode IA
    history.append({"role": "user", "content": user_input})
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=history[-10:]
        )
        answer = response.choices[0].message.content
        history.append({"role": "assistant", "content": answer})
        bot.reply_to(message, answer)
    except Exception as e:
        bot.reply_to(message, f"Erreur : {e}")

print("🚀 Daedalus Agent actif !")
bot.polling()

