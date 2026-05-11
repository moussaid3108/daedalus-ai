import os
import subprocess
import telebot
from openai import OpenAI
from dotenv import load_dotenv

# Chargement des variables (Coolify les injecte automatiquement)
load_dotenv()
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Initialisation
client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Système de mémoire simple
history = [{"role": "system", "content": "Tu es Daedalus, un agent expert en codage et administration système. Tu peux exécuter des commandes terminal via l'outil fourni. Tu es l'assistant de Kam, l'Architecte."}]

def execute_terminal(command):
    """Exécute une commande sur le serveur et renvoie le résultat"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout if result.stdout else result.stderr
        return output if output else "Commande exécutée (pas de sortie)."
    except Exception as e:
        return f"Erreur système : {str(e)}"

@bot.message_handler(func=lambda message: True)
def chat(message):
    user_input = message.text
    
    # 1. Gestion des commandes manuelles rapides
    if user_input.startswith('/exec '):
        cmd = user_input.replace('/exec ', '')
        bot.reply_to(message, f"⚙️ Exécution : `{cmd}`...")
        bot.send_message(message.chat.id, f"```\n{execute_terminal(cmd)}\n```", parse_mode="Markdown")
        return

    # 2. Mode IA intelligente (Agent)
    history.append({"role": "user", "content": user_input})
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=history[-10:] # Garde les 10 derniers messages
        )
        
        answer = response.choices[0].message.content
        history.append({"role": "assistant", "content": answer})
        bot.reply_to(message, answer)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Erreur IA : {str(e)}")

print("🚀 Daedalus Agent est prêt !")
bot.polling()

