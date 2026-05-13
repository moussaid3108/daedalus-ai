import os
from flask import Flask, render_template_string, request, jsonify
import openai

app = Flask(__name__)

# CONFIGURATION
client = openai.OpenAI(api_key=os.getenv("DEEPSEEK_KEY"), base_url="https://api.deepseek.com")

# Historique global (tu peux le vider via l'interface)
messages_history = [{"role": "system", "content": "Tu es Daedalus, un assistant élégant."}]

HTML_CODE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Daedalus AI</title>
    <style>
        :root { --bg: #000; --card: #1c1c1e; --blue: #007AFF; --text: #fff; }
        body { background: var(--bg); color: var(--text); font-family: -apple-system, system-ui, sans-serif; margin: 0; display: flex; flex-direction: column; height: 100vh; }
        header { padding: 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #222; }
        header span { font-weight: bold; color: var(--blue); }
        .btn-reset { font-size: 11px; padding: 5px 10px; border-radius: 12px; border: 1px solid #333; color: #888; text-decoration: none; }
        #chat { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 12px; }
        .msg { padding: 12px 16px; border-radius: 20px; max-width: 80%; font-size: 15px; line-height: 1.4; }
        .user { background: var(--blue); align-self: flex-end; border-bottom-right-radius: 4px; }
        .bot { background: var(--card); align-self: flex-start; border-bottom-left-radius: 4px; }
        .loading { display: none; padding: 10px; color: #666; font-size: 13px; }
        .input-area { padding: 15px; background: #000; display: flex; gap: 10px; border-top: 1px solid #222; }
        input { flex: 1; background: #1c1c1e; border: none; padding: 12px 18px; border-radius: 25px; color: white; outline: none; font-size: 16px; }
        button { background: var(--blue); border: none; width: 40px; height: 40px; border-radius: 50%; color: white; font-weight: bold; }
    </style>
</head>
<body>
    <header>
        <span>DAEDALUS</span>
        <a href="/" class="btn-reset">EFFACER TOUT</a>
    </header>
    <div id="chat">
        <div class="msg bot">Prêt, Architecte. On commence quoi ?</div>
    </div>
    <div id="loading" class="loading">Daedalus réfléchit...</div>
    <div class="input-area">
        <input type="text" id="userIn" placeholder="Message..." autocomplete="off">
        <button onclick="sendMsg()">↑</button>
    </div>

    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('userIn');
        const loader = document.getElementById('loading');

        async function sendMsg() {
            const text = input.value.trim();
            if(!text) return;

            chat.innerHTML += `<div class="msg user">${text}</div>`;
            input.value = "";
            loader.style.display = "block";
            chat.scrollTop = chat.scrollHeight;

            const res = await fetch('/ask', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({prompt: text})
            });
            const data = await res.json();
            
            loader.style.display = "none";
            chat.innerHTML += `<div class="msg bot">${data.answer}</div>`;
            chat.scrollTop = chat.scrollHeight;
        }
        input.addEventListener("keypress", (e) => { if(e.key === "Enter") sendMsg(); });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    global messages_history
    messages_history = [{"role": "system", "content": "Tu es Daedalus."}]
    return render_template_string(HTML_CODE)

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    messages_history.append({"role": "user", "content": data['prompt']})
    response = client.chat.completions.create(model="deepseek-chat", messages=messages_history[-10:])
    answer = response.choices[0].message.content
    messages_history.append({"role": "assistant", "content": answer})
    return jsonify({"answer": answer})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
