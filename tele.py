import os
import subprocess
import telebot
from openai import OpenAI

# 1. Configuration des Clés (Coolify s'en occupe)
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# 2. Initialisation des clients
client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 3. Mémoire système
history = [{"role": "system", "content": "Tu es Daedalus, l'agent de Kam. Pour coder : 1. Utilise /write fichier.py | contenu. 2. Utilise /exec python3 fichier.py pour tester. Propose toujours ces commandes à Kam pour agir sur le serveur."}]

# 4. Fonction pour exécuter des commandes terminal
def execute_terminal(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout if result.stdout else result.stderr
        return output if output else "Commande exécutée avec succès."
    except Exception as e:
        return f"Erreur Terminal : {str(e)}"

# 5. Fonction pour écrire/modifier des fichiers
def write_file(path, content):
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
        cmd = user_input.split('/exec ')[1]
        output = execute_terminal(cmd)
        bot.reply_to(message, f"```\n{output}\n```", parse_mode="Markdown")
        return

    # Commande WRITE : /write <nom_fichier> | <contenu>
    if user_input.startswith('/write '):
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
            messages=history[-10:] # Garde les 10 derniers échanges
        )
        answer = response.choices[0].message.content
        history.append({"role": "assistant", "content": answer})
        bot.reply_to(message, answer)
    except Exception as e:
        bot.reply_to(message, f"❌ Erreur IA : {str(e)}")

# 7. Lancement du bot
print("🚀 Daedalus Agent (Claude Code Mode) est prêt !")
bot.polling()

