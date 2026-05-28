import os
from flask import Flask, render_template_string, request, jsonify, redirect, url_for

from agent.loop import run_agent
from agent.workspace import create_workspace
from shop.ebay import search as ebay_search
from shop.amazon import search as amazon_search
from shop.cdiscount import search as cdiscount_search
from shop.booking import search as booking_search
from shop.skyscanner import search as sky_search
from shop.fnac import search as fnac_search

app = Flask(__name__)

API_KEY  = os.getenv("DEEPSEEK_KEY")
BASE_URL = os.getenv("BASE_URL", "https://api.deepseek.com")
MODEL    = os.getenv("MODEL", "deepseek-chat")

_, WORKSPACE = create_workspace()
messages_history = []

# -- HTML ----------------------------------------------------------------------

SHOP_HOME = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Daedalus Shop</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d1117; color: #e6edf3; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px; }
  .logo { font-size: 32px; font-weight: 800; color: #58a6ff; letter-spacing: 3px; margin-bottom: 8px; }
  .sub  { color: #8b949e; font-size: 14px; margin-bottom: 40px; }
  .search-box { width: 100%; max-width: 600px; }
  .search-row { display: flex; gap: 10px; margin-bottom: 12px; }
  input[type=text] { flex: 1; background: #161b22; border: 1px solid #30363d; border-radius: 12px; color: #e6edf3; padding: 14px 20px; font-size: 16px; outline: none; transition: border-color .15s; }
  input[type=text]:focus { border-color: #58a6ff; }
  .search-btn { background: #238636; border: none; border-radius: 12px; color: #fff; font-size: 15px; font-weight: 600; padding: 14px 20px; cursor: pointer; }
  .sources { display: flex; flex-wrap: wrap; gap: 8px; }
  .src-btn { flex: 1; min-width: 80px; padding: 9px 6px; border: 1px solid #30363d; border-radius: 10px; background: #161b22; color: #8b949e; font-size: 11px; font-weight: 600; cursor: pointer; transition: all .15s; text-align: center; }
  .src-btn.ebay.active       { border-color: #e53238; color: #e53238; }
  .src-btn.amazon.active     { border-color: #ff9900; color: #ff9900; }
  .src-btn.cdiscount.active  { border-color: #e8001c; color: #e8001c; }
  .src-btn.booking.active    { border-color: #003580; color: #003580; }
  .src-btn.skyscanner.active { border-color: #00b1ea; color: #00b1ea; }
  .src-btn.fnac.active       { border-color: #e8a319; color: #e8a319; }
  .src-btn.all.active        { border-color: #58a6ff; color: #58a6ff; }
  .trending { margin-top: 32px; text-align: center; }
  .trending p { color: #8b949e; font-size: 12px; margin-bottom: 10px; }
  .tags { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
  .tag { background: #161b22; border: 1px solid #30363d; border-radius: 20px; color: #8b949e; font-size: 12px; padding: 5px 14px; text-decoration: none; transition: all .15s; }
  .tag:hover { border-color: #58a6ff; color: #58a6ff; }
</style>
</head>
<body>
  <div class="logo">DAEDALUS</div>
  <p class="sub">Comparez les meilleures offres</p>
  <div class="search-box">
    <form id="searchForm" action="/search" method="GET">
      <input type="hidden" name="source" id="sourceInput" value="all">
      <div class="search-row">
        <input type="text" name="q" placeholder="Produit, destination, vol..." autofocus autocomplete="off">
        <button class="search-btn" type="submit">&#x1F50D;</button>
      </div>
      <div class="sources">
        <div class="src-btn ebay"       onclick="setSource('ebay')">&#x1F6D2; eBay</div>
        <div class="src-btn amazon"     onclick="setSource('amazon')">&#x1F4E6; Amazon</div>
        <div class="src-btn cdiscount"  onclick="setSource('cdiscount')">&#x1F3EA; Cdiscount</div>
        <div class="src-btn fnac"       onclick="setSource('fnac')">&#x1F3B5; Fnac</div>
        <div class="src-btn booking"    onclick="setSource('booking')">&#x1F3E8; Booking</div>
        <div class="src-btn skyscanner" onclick="setSource('skyscanner')">&#x2708;&#xFE0F; Skyscanner</div>
        <div class="src-btn all active" onclick="setSource('all')">&#x1F50D; Tout</div>
      </div>
    </form>
  </div>
  <div class="trending">
    <p>Tendances</p>
    <div class="tags">
      <a class="tag" href="/search?q=iphone+15&source=all">iPhone 15</a>
      <a class="tag" href="/search?q=air+jordan&source=ebay">Air Jordan</a>
      <a class="tag" href="/search?q=playstation+5&source=all">PS5</a>
      <a class="tag" href="/search?q=rolex&source=ebay">Rolex</a>
      <a class="tag" href="/search?q=paris&source=booking">Hotels Paris</a>
      <a class="tag" href="/search?q=barcelone&source=skyscanner">Vol Barcelone</a>
    </div>
  </div>
  <script>
    function setSource(s) {
      document.getElementById('sourceInput').value = s;
      document.querySelectorAll('.src-btn').forEach(b => b.classList.remove('active'));
      document.querySelector('.src-btn.' + s).classList.add('active');
    }
  </script>
</body>
</html>"""

SHOP_RESULTS = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>{{ query }} -- Daedalus Shop</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d1117; color: #e6edf3; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
  header { position: sticky; top: 0; z-index: 10; background: #0d1117; border-bottom: 1px solid #21262d; padding: 10px 14px; display: flex; gap: 10px; align-items: center; }
  .logo { font-weight: 800; color: #58a6ff; letter-spacing: 2px; font-size: 15px; text-decoration: none; flex-shrink: 0; }
  form { flex: 1; display: flex; gap: 8px; }
  input { flex: 1; background: #161b22; border: 1px solid #30363d; border-radius: 10px; color: #e6edf3; padding: 9px 14px; font-size: 15px; outline: none; min-width: 0; }
  input:focus { border-color: #58a6ff; }
  .search-btn { background: #238636; border: none; border-radius: 10px; color: #fff; font-size: 14px; font-weight: 600; padding: 9px 14px; cursor: pointer; }
  .tabs { display: flex; gap: 0; border-bottom: 1px solid #21262d; padding: 0 14px; overflow-x: auto; }
  .tab { padding: 10px 14px; font-size: 13px; font-weight: 600; color: #8b949e; text-decoration: none; border-bottom: 2px solid transparent; white-space: nowrap; transition: all .15s; }
  .tab.ebay:hover,       .tab.ebay.active       { color: #e53238; border-color: #e53238; }
  .tab.amazon:hover,     .tab.amazon.active     { color: #ff9900; border-color: #ff9900; }
  .tab.cdiscount:hover,  .tab.cdiscount.active  { color: #e8001c; border-color: #e8001c; }
  .tab.booking:hover,    .tab.booking.active    { color: #003580; border-color: #003580; }
  .tab.skyscanner:hover, .tab.skyscanner.active { color: #00b1ea; border-color: #00b1ea; }
  .tab.fnac:hover,       .tab.fnac.active       { color: #e8a319; border-color: #e8a319; }
  .tab.all:hover,        .tab.all.active        { color: #58a6ff; border-color: #58a6ff; }
  .meta { padding: 10px 14px; font-size: 12px; color: #8b949e; }
  .section-label { padding: 10px 14px 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #8b949e; }
  .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; padding: 0 12px 16px; }
  @media(min-width:600px){ .grid { grid-template-columns: repeat(3,1fr); } }
  @media(min-width:900px){ .grid { grid-template-columns: repeat(4,1fr); } }
  .card { background: #161b22; border: 1px solid #21262d; border-radius: 12px; overflow: hidden; text-decoration: none; color: inherit; display: flex; flex-direction: column; transition: border-color .15s, transform .15s; }
  .card:hover { transform: translateY(-2px); }
  .card.ebay:hover       { border-color: #e53238; }
  .card.amazon:hover     { border-color: #ff9900; }
  .card.cdiscount:hover  { border-color: #e8001c; }
  .card.booking:hover    { border-color: #003580; }
  .card.skyscanner:hover { border-color: #00b1ea; }
  .card.fnac:hover       { border-color: #e8a319; }
  .card img { width: 100%; aspect-ratio: 1; object-fit: contain; background: #0d1117; padding: 8px; }
  .no-img { aspect-ratio: 1; background: #21262d; display: flex; align-items: center; justify-content: center; font-size: 28px; }
  .card-body { padding: 10px; flex: 1; display: flex; flex-direction: column; gap: 5px; }
  .card-title { font-size: 12px; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .card-price { font-size: 15px; font-weight: 700; }
  .card.ebay       .card-price { color: #e53238; }
  .card.amazon     .card-price { color: #ff9900; }
  .card.cdiscount  .card-price { color: #e8001c; }
  .card.booking    .card-price { color: #003580; }
  .card.skyscanner .card-price { color: #00b1ea; }
  .card.fnac       .card-price { color: #e8a319; }
  .card-condition { font-size: 11px; color: #8b949e; }
  .card-btn { margin-top: auto; border: none; border-radius: 8px; color: #fff; font-size: 11px; font-weight: 600; padding: 7px; text-align: center; }
  .card.ebay       .card-btn { background: #e53238; }
  .card.amazon     .card-btn { background: #ff9900; color: #000; }
  .card.cdiscount  .card-btn { background: #e8001c; }
  .card.booking    .card-btn { background: #003580; }
  .card.skyscanner .card-btn { background: #00b1ea; }
  .card.fnac       .card-btn { background: #e8a319; color: #000; }
  .error { padding: 40px 20px; text-align: center; color: #ff7b72; font-size: 14px; }
  .empty { padding: 60px 20px; text-align: center; color: #8b949e; }
</style>
</head>
<body>
<header>
  <a class="logo" href="/">DAE</a>
  <form action="/search" method="GET">
    <input type="hidden" name="source" value="{{ source }}">
    <input type="text" name="q" value="{{ query }}" autocomplete="off">
    <button class="search-btn" type="submit">&#x1F50D;</button>
  </form>
</header>

<div class="tabs">
  <a class="tab all        {% if source=='all'        %}active{% endif %}" href="/search?q={{ query }}&source=all">&#x1F50D; Tout</a>
  <a class="tab ebay       {% if source=='ebay'       %}active{% endif %}" href="/search?q={{ query }}&source=ebay">&#x1F6D2; eBay</a>
  <a class="tab amazon     {% if source=='amazon'     %}active{% endif %}" href="/search?q={{ query }}&source=amazon">&#x1F4E6; Amazon</a>
  <a class="tab cdiscount  {% if source=='cdiscount'  %}active{% endif %}" href="/search?q={{ query }}&source=cdiscount">&#x1F3EA; Cdiscount</a>
  <a class="tab fnac       {% if source=='fnac'       %}active{% endif %}" href="/search?q={{ query }}&source=fnac">&#x1F3B5; Fnac</a>
  <a class="tab booking    {% if source=='booking'    %}active{% endif %}" href="/search?q={{ query }}&source=booking">&#x1F3E8; Booking</a>
  <a class="tab skyscanner {% if source=='skyscanner' %}active{% endif %}" href="/search?q={{ query }}&source=skyscanner">&#x2708; Skyscanner</a>
</div>

{% if error %}
  <div class="error">{{ error }}</div>
{% elif not ebay_items and not amazon_items and not cdiscount_items and not booking_items and not sky_items and not fnac_items %}
  <div class="empty">Aucun resultat pour "{{ query }}"</div>
{% else %}
  {% set total = ebay_items|length + amazon_items|length + cdiscount_items|length + booking_items|length + sky_items|length + fnac_items|length %}
  <p class="meta">{{ total }} resultat(s) pour <strong>{{ query }}</strong></p>

  {% if ebay_items %}
    {% if source == 'all' %}<p class="section-label">&#x1F6D2; eBay</p>{% endif %}
    <div class="grid">
      {% for item in ebay_items %}
      <a class="card ebay" href="{{ item.url }}" target="_blank" rel="noopener">
        {% if item.image %}<img src="{{ item.image }}" alt="{{ item.title }}" loading="lazy">
        {% else %}<div class="no-img">&#x1F4E6;</div>{% endif %}
        <div class="card-body">
          <p class="card-title">{{ item.title }}</p>
          <p class="card-price">{{ item.price }} {{ item.currency }}</p>
          {% if item.condition %}<p class="card-condition">{{ item.condition }}</p>{% endif %}
          <div class="card-btn">Voir sur eBay</div>
        </div>
      </a>
      {% endfor %}
    </div>
  {% endif %}

  {% if amazon_items %}
    {% if source == 'all' %}<p class="section-label">&#x1F4E6; Amazon</p>{% endif %}
    <div class="grid">
      {% for item in amazon_items %}
      <a class="card amazon" href="{{ item.url }}" target="_blank" rel="noopener">
        {% if item.image %}<img src="{{ item.image }}" alt="{{ item.title }}" loading="lazy">
        {% else %}<div class="no-img">&#x1F4E6;</div>{% endif %}
        <div class="card-body">
          <p class="card-title">{{ item.title }}</p>
          <p class="card-price">{{ item.price }}</p>
          <div class="card-btn">Voir sur Amazon</div>
        </div>
      </a>
      {% endfor %}
    </div>
  {% endif %}

  {% if cdiscount_items %}
    {% if source == 'all' %}<p class="section-label">&#x1F3EA; Cdiscount</p>{% endif %}
    <div class="grid">
      {% for item in cdiscount_items %}
      <a class="card cdiscount" href="{{ item.url }}" target="_blank" rel="noopener">
        {% if item.image %}<img src="{{ item.image }}" alt="{{ item.title }}" loading="lazy">
        {% else %}<div class="no-img">&#x1F4E6;</div>{% endif %}
        <div class="card-body">
          <p class="card-title">{{ item.title }}</p>
          <p class="card-price">{{ item.price }} EUR</p>
          {% if item.condition %}<p class="card-condition">{{ item.condition }}</p>{% endif %}
          <div class="card-btn">Voir sur Cdiscount</div>
        </div>
      </a>
      {% endfor %}
    </div>
  {% endif %}

  {% if fnac_items %}
    {% if source == 'all' %}<p class="section-label">&#x1F3B5; Fnac</p>{% endif %}
    <div class="grid">
      {% for item in fnac_items %}
      <a class="card fnac" href="{{ item.url }}" target="_blank" rel="noopener">
        {% if item.image %}<img src="{{ item.image }}" alt="{{ item.title }}" loading="lazy">
        {% else %}<div class="no-img">&#x1F3B5;</div>{% endif %}
        <div class="card-body">
          <p class="card-title">{{ item.title }}</p>
          <p class="card-price">{{ item.price }} EUR</p>
          {% if item.condition %}<p class="card-condition">{{ item.condition }}</p>{% endif %}
          <div class="card-btn">Voir sur Fnac</div>
        </div>
      </a>
      {% endfor %}
    </div>
  {% endif %}

  {% if booking_items %}
    {% if source == 'all' %}<p class="section-label">&#x1F3E8; Booking</p>{% endif %}
    <div class="grid">
      {% for item in booking_items %}
      <a class="card booking" href="{{ item.url }}" target="_blank" rel="noopener">
        {% if item.image %}<img src="{{ item.image }}" alt="{{ item.title }}" loading="lazy">
        {% else %}<div class="no-img">&#x1F3E8;</div>{% endif %}
        <div class="card-body">
          <p class="card-title">{{ item.title }}</p>
          {% if item.location %}<p class="card-condition">{{ item.location }}</p>{% endif %}
          {% if item.price %}<p class="card-price">A partir de {{ item.price }} EUR</p>{% endif %}
          {% if item.condition %}<p class="card-condition">{{ item.condition }}</p>{% endif %}
          <div class="card-btn">Reserver sur Booking</div>
        </div>
      </a>
      {% endfor %}
    </div>
  {% endif %}

  {% if sky_items %}
    {% if source == 'all' %}<p class="section-label">&#x2708; Skyscanner</p>{% endif %}
    <div class="grid">
      {% for item in sky_items %}
      <a class="card skyscanner" href="{{ item.url }}" target="_blank" rel="noopener">
        {% if item.image %}<img src="{{ item.image }}" alt="{{ item.title }}" loading="lazy">
        {% else %}<div class="no-img">&#x2708;</div>{% endif %}
        <div class="card-body">
          <p class="card-title">{{ item.title }}</p>
          {% if item.price %}<p class="card-price">{{ item.price }} EUR</p>{% endif %}
          {% if item.condition %}<p class="card-condition">{{ item.condition }}</p>{% endif %}
          <div class="card-btn">Voir sur Skyscanner</div>
        </div>
      </a>
      {% endfor %}
    </div>
  {% endif %}
{% endif %}
</body>
</html>"""

CHAT_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Daedalus AI</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #000; color: #fff; font-family: -apple-system, system-ui, sans-serif; display: flex; flex-direction: column; height: 100vh; }
  header { padding: 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #222; }
  header span { font-weight: bold; color: #007AFF; }
  .btn-reset { font-size: 11px; padding: 5px 10px; border-radius: 12px; border: 1px solid #333; color: #888; text-decoration: none; }
  #chat { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 12px; }
  .msg { padding: 12px 16px; border-radius: 20px; max-width: 80%; font-size: 15px; line-height: 1.4; }
  .user { background: #007AFF; align-self: flex-end; border-bottom-right-radius: 4px; }
  .bot  { background: #1c1c1e; align-self: flex-start; border-bottom-left-radius: 4px; }
  .loading { display: none; padding: 10px; color: #666; font-size: 13px; }
  .input-area { padding: 15px; background: #000; display: flex; gap: 10px; border-top: 1px solid #222; }
  input { flex: 1; background: #1c1c1e; border: none; padding: 12px 18px; border-radius: 25px; color: white; outline: none; font-size: 16px; }
  button { background: #007AFF; border: none; width: 40px; height: 40px; border-radius: 50%; color: white; font-weight: bold; }
</style>
</head>
<body>
  <header><span>DAEDALUS</span><a href="/daedalus" class="btn-reset">EFFACER</a></header>
  <div id="chat"><div class="msg bot">Pret, Architecte.</div></div>
  <div id="loading" class="loading">Daedalus reflechit...</div>
  <div class="input-area">
    <input type="text" id="userIn" placeholder="Message..." autocomplete="off">
    <button onclick="sendMsg()">&#x2191;</button>
  </div>
  <script>
    const chat=document.getElementById('chat'),input=document.getElementById('userIn'),loader=document.getElementById('loading');
    async function sendMsg(){
      const text=input.value.trim(); if(!text)return;
      chat.innerHTML+=`<div class="msg user">${text}</div>`; input.value="";
      loader.style.display="block"; chat.scrollTop=chat.scrollHeight;
      const res=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:text})});
      const data=await res.json(); loader.style.display="none";
      chat.innerHTML+=`<div class="msg bot">${data.answer}</div>`; chat.scrollTop=chat.scrollHeight;
    }
    input.addEventListener("keypress",(e)=>{if(e.key==="Enter")sendMsg();});
  </script>
</body>
</html>"""

# -- Routes --------------------------------------------------------------------

@app.route("/")
def home():
    return render_template_string(SHOP_HOME)

@app.route("/search")
def search():
    query  = request.args.get("q", "").strip()
    source = request.args.get("source", "all")
    if not query:
        return redirect(url_for("home"))

    ebay_items, amazon_items, cdiscount_items = [], [], []
    booking_items, sky_items, fnac_items = [], [], []
    error = None
    try:
        if source in ("ebay", "all"):
            ebay_items = ebay_search(query)
        if source in ("amazon", "all"):
            amazon_items = amazon_search(query)
        if source in ("cdiscount", "all"):
            cdiscount_items = cdiscount_search(query)
        if source in ("fnac", "all"):
            fnac_items = fnac_search(query)
        if source in ("booking", "all"):
            booking_items = booking_search(query)
        if source == "skyscanner":
            sky_items = sky_search(query)
    except Exception as e:
        error = str(e)

    return render_template_string(
        SHOP_RESULTS,
        query=query, source=source,
        ebay_items=ebay_items,
        amazon_items=amazon_items,
        cdiscount_items=cdiscount_items,
        fnac_items=fnac_items,
        booking_items=booking_items,
        sky_items=sky_items,
        error=error,
    )

@app.route("/daedalus")
def daedalus():
    global messages_history
    messages_history = []
    return render_template_string(CHAT_HTML)

@app.route("/ask", methods=["POST"])
def ask():
    global messages_history
    user_msg = (request.json or {}).get("prompt", "").strip()
    if not user_msg:
        return jsonify({"answer": "Message vide."})
    messages_history.append({"role": "user", "content": user_msg})
    try:
        answer, messages_history, _ = run_agent(
            messages_history, api_key=API_KEY,
            base_url=BASE_URL, model=MODEL, workspace=WORKSPACE,
        )
        return jsonify({"answer": answer})
    except Exception as e:
        messages_history.pop()
        return jsonify({"answer": f"Erreur : {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
