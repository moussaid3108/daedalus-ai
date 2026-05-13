import os
import subprocess
import telebot
from openai import OpenAI

# 1. Configuration des Clés (Coolify s'en occupe)
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

BLOCKED_COMMANDS = ("rm ", "rmdir", "mkfs", "dd ", "shutdown", "reboot", ":(){ :|:& };:", "> /dev/", "curl ", "wget ")

# 2. Initialisation des clients
client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 3. Mémoire système
history = [{"role": "system", "content": "Tu es Daedalus, l'agent de Kam. Pour coder : 1. Utilise /write fichier.py | contenu. 2. Utilise /exec python3 fichier.py pour tester. Propose toujours ces commandes à Kam pour agir sur le serveur."}]

def is_authorized(message):
    return ALLOWED_USER_ID and message.from_user.id == ALLOWED_USER_ID

# 4. Fonction pour exécuter des commandes terminal
def execute_terminal(command):
    if any(pattern in command for pattern in BLOCKED_COMMANDS):
        return "⛔ Commande refusée."
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout if result.stdout else result.stderr
        return output if output else "Commande exécutée avec succès."
    except Exception as e:
        return f"Erreur Terminal : {str(e)}"

# 5. Fonction pour écrire/modifier des fichiers
def write_file(path, content):
    # Interdit les chemins absolus et les traversées de répertoire
    if path.startswith("/") or ".." in path:
        return "⛔ Chemin non autorisé."
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"✅ Fichier '{path}' créé ou mis à jour avec succès !"
    except Exception as e:
        return f"❌ Erreur d'écriture : {str(e)}"

# 6. Gestionnaire de messages
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_input = message.text

    # Commande EXEC : /exec <commande>
    if user_input.startswith('/exec '):
        if not is_authorized(message):
            bot.reply_to(message, "⛔ Accès refusé.")
            return
        cmd = user_input.split('/exec ')[1]
        output = execute_terminal(cmd)
        bot.reply_to(message, f"```\n{output}\n```", parse_mode="Markdown")
        return

    # Commande WRITE : /write <nom_fichier> | <contenu>
    if user_input.startswith('/write '):
        if not is_authorized(message):
            bot.reply_to(message, "⛔ Accès refusé.")
            return
        try:
            parts = user_input.replace('/write ', '').split('|', 1)
            filename = parts[0].strip()
            content = parts[1].strip()
            res = write_file(filename, content)
            bot.reply_to(message, res)
        except:
            bot.reply_to(message, "⚠️ Format requis : `/write fichier.py | contenu du code`", parse_mode="Markdown")
        return

    # Mode IA Conversationnelle
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
        bot.reply_to(message, f"❌ Erreur IA : {str(e)}")

# 7. Lancement du bot
print("🚀 Daedalus Agent (Claude Code Mode) est prêt !")
bot.polling()
