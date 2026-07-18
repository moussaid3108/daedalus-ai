import os, json, random, string
from datetime import datetime
from functools import wraps
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "inpirequest-secret-2024")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inpirequest.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# ══════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════

class User(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    prenom     = db.Column(db.String(100), nullable=False)
    nom        = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(200), unique=True, nullable=False)
    password   = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    procedures = db.relationship("Procedure", backref="user", lazy=True)

class Procedure(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    type       = db.Column(db.String(50), nullable=False)
    phase      = db.Column(db.Integer, nullable=True)   # 1/2/3 pour dissolution, None pour création
    parent_id  = db.Column(db.Integer, db.ForeignKey("procedure.id"), nullable=True)
    societe    = db.Column(db.String(200), default="")
    status     = db.Column(db.String(50), default="formulaire")
    data       = db.Column(db.Text, default="{}")
    prix       = db.Column(db.Float, default=0)
    ref        = db.Column(db.String(20), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    children   = db.relationship("Procedure", backref=db.backref("parent", remote_side="Procedure.id"), lazy=True)

with app.app_context():
    db.create_all()


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

def get_user():
    if "user_id" in session:
        return User.query.get(session["user_id"])
    return None

def make_ref(type_, id_, phase=None):
    prefix = "DIS" if type_ == "dissolution" else "CRE"
    if phase:
        return f"{prefix}-P{phase}-{datetime.now().year}-{id_:04d}"
    return f"{prefix}-{datetime.now().year}-{id_:04d}"

STATUS = {
    "en_attente": ("🔒", "En attente",  "#64748B"),
    "formulaire": ("📝", "Formulaire",  "#F59E0B"),
    "documents":  ("📄", "Documents",   "#3B82F6"),
    "signature":  ("✍️",  "Signature",   "#8B5CF6"),
    "paiement":   ("💳", "Paiement",    "#EC4899"),
    "depose":     ("⚙️",  "Déposé INPI", "#F97316"),
    "termine":    ("✅", "Terminé",     "#10B981"),
}

PRIX = {"dissolution": 299, "creation": 499}


# ══════════════════════════════════════════════════════════════════
# CSS GLOBAL
# ══════════════════════════════════════════════════════════════════

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#060B18;--card:#0D1528;--card2:#13213D;--border:#1E3A5A;
  --gold:#C9A84C;--gold2:#E8C86C;
  --text:#F1F5F9;--text2:#94A3B8;--text3:#64748B;
  --green:#10B981;--blue:#3B82F6;--purple:#8B5CF6;
  --red:#EF4444;--orange:#F97316;
}
body{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;min-height:100vh}
a{color:inherit;text-decoration:none}
input,select,textarea{
  background:var(--card2);border:1px solid var(--border);border-radius:10px;
  color:var(--text);padding:12px 16px;width:100%;font-size:15px;outline:none;
  transition:.2s
}
input:focus,select:focus,textarea:focus{border-color:var(--gold);box-shadow:0 0 0 3px rgba(201,168,76,.15)}
select option{background:var(--card)}
label{display:block;font-size:13px;color:var(--text2);margin-bottom:6px;font-weight:500}
.btn{
  display:inline-flex;align-items:center;gap:8px;padding:13px 28px;
  border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;
  border:none;transition:.2s;text-decoration:none
}
.btn-gold{background:linear-gradient(135deg,var(--gold),var(--gold2));color:#0A0E1A}
.btn-gold:hover{transform:translateY(-1px);box-shadow:0 8px 25px rgba(201,168,76,.4)}
.btn-outline{background:transparent;border:1.5px solid var(--border);color:var(--text2)}
.btn-outline:hover{border-color:var(--gold);color:var(--gold)}
.btn-ghost{background:rgba(201,168,76,.1);color:var(--gold);border:1px solid rgba(201,168,76,.2)}
.btn-ghost:hover{background:rgba(201,168,76,.2)}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px}
.badge{
  display:inline-flex;align-items:center;gap:5px;
  padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600
}
.flash{padding:14px 20px;border-radius:10px;margin-bottom:20px;font-size:14px}
.flash.error{background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.3);color:#FCA5A5}
.flash.success{background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.3);color:#6EE7B7}
/* Nav */
nav{
  position:sticky;top:0;z-index:100;
  background:rgba(6,11,24,.85);backdrop-filter:blur(20px);
  border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;
  padding:0 5%;height:68px
}
.logo{font-size:22px;font-weight:800;letter-spacing:-0.5px}
.logo span{color:var(--gold)}
.nav-links{display:flex;align-items:center;gap:32px}
.nav-links a{color:var(--text2);font-size:14px;font-weight:500;transition:.2s}
.nav-links a:hover{color:var(--text)}
.nav-actions{display:flex;align-items:center;gap:12px}
/* Grid */
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
@media(max-width:768px){.grid2,.grid3{grid-template-columns:1fr}}
/* Steps */
.steps{display:flex;align-items:center;justify-content:center;gap:0;margin-bottom:40px}
.step{display:flex;flex-direction:column;align-items:center;gap:8px;flex:1;position:relative}
.step:not(:last-child)::after{
  content:'';position:absolute;top:20px;left:50%;width:100%;
  height:2px;background:var(--border);z-index:0
}
.step.active:not(:last-child)::after{background:var(--gold)}
.step-circle{
  width:40px;height:40px;border-radius:50%;border:2px solid var(--border);
  background:var(--card);display:flex;align-items:center;justify-content:center;
  font-size:14px;font-weight:700;z-index:1;color:var(--text2);transition:.3s
}
.step.active .step-circle{border-color:var(--gold);background:var(--gold);color:#0A0E1A}
.step.done .step-circle{border-color:var(--green);background:var(--green);color:#fff}
.step-label{font-size:11px;color:var(--text2);font-weight:500;text-align:center}
.step.active .step-label{color:var(--gold)}
/* Form step panels */
.step-panel{display:none}.step-panel.active{display:block}
/* Divider */
.divider{height:1px;background:var(--border);margin:24px 0}
/* Stat card */
.stat{text-align:center}
.stat-val{font-size:36px;font-weight:800;color:var(--gold);line-height:1}
.stat-lbl{font-size:13px;color:var(--text2);margin-top:4px}
"""

# ══════════════════════════════════════════════════════════════════
# TEMPLATES
# ══════════════════════════════════════════════════════════════════

def base(title, content, user=None):
    u = user or get_user()
    nav_right = f"""
      <a class="btn btn-outline" href="{url_for('login')}">Se connecter</a>
      <a class="btn btn-gold" href="{url_for('register')}">S'inscrire</a>
    """ if not u else f"""
      <a class="btn btn-ghost" href="{url_for('dashboard')}">Mon espace</a>
      <a class="btn btn-outline" href="{url_for('logout')}">Déconnexion</a>
    """
    flashes = ""
    for cat, msg in (session.pop("_flashes", None) or []):
        c = "error" if cat == "error" else "success"
        flashes += f'<div class="flash {c}">{msg}</div>'
    return render_template_string(f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — INPIrequest</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<nav>
  <a class="logo" href="{url_for('landing')}">INPI<span>request</span></a>
  <div class="nav-links">
    <a href="{url_for('landing')}#services">Services</a>
    <a href="{url_for('landing')}#tarifs">Tarifs</a>
    <a href="{url_for('landing')}#comment">Comment ça marche</a>
  </div>
  <div class="nav-actions">{nav_right}</div>
</nav>
<div style="max-width:1200px;margin:0 auto;padding:0 5%">
  {flashes}
  {content}
</div>
</body></html>""")


# ──────────────────────────────────────────────────────────────────
# LANDING
# ──────────────────────────────────────────────────────────────────

LANDING = """
<style>
.hero{
  text-align:center;padding:100px 0 80px;
  background:radial-gradient(ellipse 80% 60% at 50% -10%,rgba(201,168,76,.15),transparent)
}
.hero h1{font-size:clamp(36px,5vw,62px);font-weight:800;letter-spacing:-1.5px;line-height:1.1;margin-bottom:20px}
.hero h1 span{
  background:linear-gradient(135deg,var(--gold),var(--gold2));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent
}
.hero p{font-size:18px;color:var(--text2);max-width:560px;margin:0 auto 40px;line-height:1.6}
.hero-btns{display:flex;gap:16px;justify-content:center;flex-wrap:wrap}
.hero-badge{
  display:inline-flex;align-items:center;gap:8px;
  background:rgba(201,168,76,.1);border:1px solid rgba(201,168,76,.25);
  border-radius:30px;padding:8px 20px;font-size:13px;color:var(--gold);
  margin-bottom:32px
}
.services-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin:60px 0}
@media(max-width:768px){.services-grid{grid-template-columns:1fr}}
.service-card{
  background:var(--card);border:1px solid var(--border);border-radius:20px;
  padding:36px;transition:.3s;cursor:pointer;position:relative;overflow:hidden
}
.service-card::before{
  content:'';position:absolute;inset:0;
  background:radial-gradient(circle at 80% 20%,rgba(201,168,76,.06),transparent 60%);
  opacity:0;transition:.3s
}
.service-card:hover{border-color:rgba(201,168,76,.4);transform:translateY(-3px)}
.service-card:hover::before{opacity:1}
.service-icon{font-size:48px;margin-bottom:20px}
.service-card h3{font-size:22px;font-weight:700;margin-bottom:10px}
.service-card p{color:var(--text2);font-size:15px;line-height:1.6;margin-bottom:20px}
.service-price{font-size:28px;font-weight:800;color:var(--gold)}
.service-price span{font-size:14px;font-weight:400;color:var(--text2)}
.service-features{list-style:none;margin-top:16px;display:flex;flex-direction:column;gap:8px}
.service-features li{font-size:14px;color:var(--text2);display:flex;align-items:center;gap:8px}
.service-features li::before{content:'✓';color:var(--green);font-weight:700}
.section-title{text-align:center;margin:80px 0 48px}
.section-title h2{font-size:36px;font-weight:800;letter-spacing:-0.5px;margin-bottom:12px}
.section-title p{color:var(--text2);font-size:16px}
.how-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-bottom:80px}
@media(max-width:768px){.how-grid{grid-template-columns:1fr 1fr}}
.how-card{text-align:center;padding:28px 20px}
.how-num{
  width:48px;height:48px;border-radius:50%;
  background:linear-gradient(135deg,var(--gold),var(--gold2));
  color:#0A0E1A;font-weight:800;font-size:18px;
  display:flex;align-items:center;justify-content:center;margin:0 auto 16px
}
.how-card h4{font-size:15px;font-weight:700;margin-bottom:8px}
.how-card p{font-size:13px;color:var(--text2);line-height:1.5}
.trust-bar{
  display:flex;justify-content:center;gap:48px;flex-wrap:wrap;
  padding:40px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);
  margin:60px 0
}
.trust-item{text-align:center}
.trust-val{font-size:28px;font-weight:800;color:var(--gold)}
.trust-lbl{font-size:13px;color:var(--text2);margin-top:4px}
footer{
  text-align:center;padding:40px 0;color:var(--text3);
  font-size:13px;border-top:1px solid var(--border);margin-top:60px
}
</style>

<div class="hero">
  <div class="hero-badge">⚡ 100% en ligne · Livraison sous 48h</div>
  <h1>Vos formalités <span>INPI</span><br>en quelques clics</h1>
  <p>Créez ou fermez votre société sans vous déplacer. Générez vos documents depuis nos modèles standardisés — nous déposons à l'INPI à votre place en tant que mandataire.</p>
  <div class="hero-btns">
    <a class="btn btn-gold" href="#services" style="font-size:16px;padding:16px 36px">Démarrer</a>
    <a class="btn btn-outline" href="#comment" style="font-size:16px;padding:16px 36px">Comment ça marche</a>
  </div>
</div>

<div class="trust-bar">
  <div class="trust-item"><div class="trust-val">100%</div><div class="trust-lbl">Taux d'acceptation INPI</div></div>
  <div class="trust-item"><div class="trust-val">48h</div><div class="trust-lbl">Délai de traitement</div></div>
  <div class="trust-item"><div class="trust-val">eIDAS</div><div class="trust-lbl">Signature qualifiée</div></div>
  <div class="trust-item"><div class="trust-val">RGPD</div><div class="trust-lbl">Données sécurisées</div></div>
</div>

<div id="services">
  <div class="section-title">
    <h2>Nos services</h2>
    <p>Deux formalités, une seule plateforme</p>
  </div>
  <div class="services-grid">
    <div class="service-card" onclick="location.href='/dissolution'">
      <div class="service-icon">🏢</div>
      <h3>Dissolution & Radiation</h3>
      <p>Fermez votre société en toute sérénité. Générez vos documents via nos modèles, signez en ligne — nous déposons le dossier à l'INPI en tant que mandataire.</p>
      <div class="service-price">299€ <span>TTC tout inclus</span></div>
      <ul class="service-features">
        <li>PV d'Assemblée Générale</li>
        <li>Annonce légale incluse</li>
        <li>Signature électronique eIDAS</li>
        <li>Dépôt Guichet Unique INPI</li>
        <li>Certificat de radiation</li>
      </ul>
    </div>
    <div class="service-card" onclick="location.href='/creation'">
      <div class="service-icon">🚀</div>
      <h3>Création de société</h3>
      <p>Lancez votre activité rapidement. Statuts générés depuis nos modèles, INPI déposé, Kbis livré.</p>
      <div class="service-price">499€ <span>TTC tout inclus</span></div>
      <ul class="service-features">
        <li>SAS · SARL · SCI · EURL</li>
        <li>Modèles de statuts self-service</li>
        <li>Annonce légale incluse</li>
        <li>Signature électronique eIDAS</li>
        <li>Dépôt INPI + Kbis</li>
      </ul>
    </div>
  </div>
</div>

<div id="comment">
  <div class="section-title">
    <h2>Comment ça marche</h2>
    <p>4 étapes simples, on s'occupe du reste</p>
  </div>
  <div class="how-grid">
    <div class="how-card">
      <div class="how-num">1</div>
      <h4>Formulaire en ligne</h4>
      <p>Remplissez les infos de votre société en 5 minutes</p>
    </div>
    <div class="how-card">
      <div class="how-num">2</div>
      <h4>Génération des documents</h4>
      <p>Vos PV et documents légaux générés automatiquement</p>
    </div>
    <div class="how-card">
      <div class="how-num">3</div>
      <h4>Signature électronique</h4>
      <p>Signez en ligne avec votre téléphone — valeur juridique eIDAS</p>
    </div>
    <div class="how-card">
      <div class="how-num">4</div>
      <h4>Dépôt INPI</h4>
      <p>Nous déposons à votre place sur le Guichet Unique INPI</p>
    </div>
  </div>
</div>

<div id="tarifs">
  <div class="section-title">
    <h2>Tarifs transparents</h2>
    <p>Aucun frais caché. Prix TTC, tout inclus.</p>
  </div>
  <div class="grid2" style="max-width:700px;margin:0 auto 48px">
    <div class="card" style="text-align:center;border-color:rgba(201,168,76,.3)">
      <div style="font-size:40px;margin-bottom:16px">🏢</div>
      <h3 style="font-size:20px;margin-bottom:8px">Dissolution</h3>
      <div style="font-size:48px;font-weight:800;color:var(--gold);margin:16px 0">299€</div>
      <p style="color:var(--text2);font-size:13px;margin-bottom:24px">Annonce légale + INPI inclus</p>
      <a class="btn btn-gold" style="width:100%;justify-content:center" href="/dissolution">Commencer</a>
    </div>
    <div class="card" style="text-align:center;border-color:rgba(59,130,246,.3)">
      <div style="font-size:40px;margin-bottom:16px">🚀</div>
      <h3 style="font-size:20px;margin-bottom:8px">Création</h3>
      <div style="font-size:48px;font-weight:800;color:var(--blue);margin:16px 0">499€</div>
      <p style="color:var(--text2);font-size:13px;margin-bottom:24px">Statuts + annonce légale + INPI</p>
      <a class="btn" style="width:100%;justify-content:center;background:var(--blue);color:#fff" href="/creation">Commencer</a>
    </div>
  </div>

  <!-- COMPARATIF -->
  <div style="max-width:900px;margin:0 auto 80px">
    <div style="text-align:center;margin-bottom:32px">
      <div style="display:inline-flex;align-items:center;gap:8px;background:rgba(16,185,129,.1);
           border:1px solid rgba(16,185,129,.3);border-radius:30px;padding:8px 20px;
           font-size:13px;color:var(--green);font-weight:600;margin-bottom:16px">
        🔍 Le vrai coût chez la concurrence
      </div>
      <h3 style="font-size:22px;font-weight:800;margin-bottom:8px">Pourquoi INPIrequest coûte moins cher au final</h3>
      <p style="color:var(--text2);font-size:15px">Les plateformes affichent des prix bas mais facturent chaque étape séparément.</p>
    </div>

    <!-- Tableau Dissolution -->
    <div class="card" style="margin-bottom:20px;padding:0;overflow:hidden">
      <div style="background:rgba(201,168,76,.08);border-bottom:1px solid var(--border);
           padding:16px 24px;display:flex;align-items:center;gap:10px">
        <span style="font-size:20px">🏢</span>
        <span style="font-weight:700;font-size:16px">Dissolution & Radiation</span>
      </div>
      <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:14px">
          <thead>
            <tr style="border-bottom:1px solid var(--border)">
              <th style="text-align:left;padding:14px 24px;color:var(--text2);font-weight:600">Prestation</th>
              <th style="text-align:center;padding:14px 16px;color:var(--text2);font-weight:600">Concurrents</th>
              <th style="text-align:center;padding:14px 16px;color:var(--gold);font-weight:700">INPIrequest</th>
            </tr>
          </thead>
          <tbody>
            <tr style="border-bottom:1px solid rgba(30,58,90,.5)">
              <td style="padding:13px 24px">Honoraires de traitement</td>
              <td style="text-align:center;padding:13px 16px;color:var(--text2)">~100€</td>
              <td style="text-align:center;padding:13px 16px;color:var(--gold);font-weight:600">inclus</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(30,58,90,.5)">
              <td style="padding:13px 24px">Annonce légale (dissolution)</td>
              <td style="text-align:center;padding:13px 16px;color:var(--text2)">~180€ en sus</td>
              <td style="text-align:center;padding:13px 16px;color:var(--gold);font-weight:600">inclus</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(30,58,90,.5)">
              <td style="padding:13px 24px">Dépôt Guichet Unique INPI</td>
              <td style="text-align:center;padding:13px 16px;color:var(--text2)">~50€ en sus</td>
              <td style="text-align:center;padding:13px 16px;color:var(--gold);font-weight:600">inclus</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(30,58,90,.5)">
              <td style="padding:13px 24px">Signature électronique eIDAS</td>
              <td style="text-align:center;padding:13px 16px;color:var(--text2)">~30€ en sus</td>
              <td style="text-align:center;padding:13px 16px;color:var(--gold);font-weight:600">inclus</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(30,58,90,.5)">
              <td style="padding:13px 24px">Génération PV & documents légaux</td>
              <td style="text-align:center;padding:13px 16px;color:var(--red)">✗ non inclus</td>
              <td style="text-align:center;padding:13px 16px;color:var(--gold);font-weight:600">inclus</td>
            </tr>
            <tr style="background:rgba(201,168,76,.06)">
              <td style="padding:14px 24px;font-weight:700">Total réel</td>
              <td style="text-align:center;padding:14px 16px;font-weight:800;color:var(--red);font-size:18px">~360€+</td>
              <td style="text-align:center;padding:14px 16px;font-weight:800;color:var(--gold);font-size:18px">299€</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tableau Création -->
    <div class="card" style="padding:0;overflow:hidden">
      <div style="background:rgba(59,130,246,.08);border-bottom:1px solid var(--border);
           padding:16px 24px;display:flex;align-items:center;gap:10px">
        <span style="font-size:20px">🚀</span>
        <span style="font-weight:700;font-size:16px">Création de société</span>
      </div>
      <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:14px">
          <thead>
            <tr style="border-bottom:1px solid var(--border)">
              <th style="text-align:left;padding:14px 24px;color:var(--text2);font-weight:600">Prestation</th>
              <th style="text-align:center;padding:14px 16px;color:var(--text2);font-weight:600">Concurrents</th>
              <th style="text-align:center;padding:14px 16px;color:var(--blue);font-weight:700">INPIrequest</th>
            </tr>
          </thead>
          <tbody>
            <tr style="border-bottom:1px solid rgba(30,58,90,.5)">
              <td style="padding:13px 24px">Honoraires de traitement</td>
              <td style="text-align:center;padding:13px 16px;color:var(--text2)">~199€</td>
              <td style="text-align:center;padding:13px 16px;color:var(--blue);font-weight:600">inclus</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(30,58,90,.5)">
              <td style="padding:13px 24px">Modèles de statuts standardisés</td>
              <td style="text-align:center;padding:13px 16px;color:var(--text2)">~100€ en sus</td>
              <td style="text-align:center;padding:13px 16px;color:var(--blue);font-weight:600">inclus</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(30,58,90,.5)">
              <td style="padding:13px 24px">Annonce légale (constitution)</td>
              <td style="text-align:center;padding:13px 16px;color:var(--text2)">~180€ en sus</td>
              <td style="text-align:center;padding:13px 16px;color:var(--blue);font-weight:600">inclus</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(30,58,90,.5)">
              <td style="padding:13px 24px">Dépôt INPI + Kbis</td>
              <td style="text-align:center;padding:13px 16px;color:var(--text2)">~50€ en sus</td>
              <td style="text-align:center;padding:13px 16px;color:var(--blue);font-weight:600">inclus</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(30,58,90,.5)">
              <td style="padding:13px 24px">Signature électronique eIDAS</td>
              <td style="text-align:center;padding:13px 16px;color:var(--text2)">~30€ en sus</td>
              <td style="text-align:center;padding:13px 16px;color:var(--blue);font-weight:600">inclus</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(30,58,90,.5)">
              <td style="padding:13px 24px">Accompagnement dédié</td>
              <td style="text-align:center;padding:13px 16px;color:var(--red)">✗ non inclus</td>
              <td style="text-align:center;padding:13px 16px;color:var(--blue);font-weight:600">inclus</td>
            </tr>
            <tr style="background:rgba(59,130,246,.06)">
              <td style="padding:14px 24px;font-weight:700">Total réel</td>
              <td style="text-align:center;padding:14px 16px;font-weight:800;color:var(--red);font-size:18px">~559€+</td>
              <td style="text-align:center;padding:14px 16px;font-weight:800;color:var(--blue);font-size:18px">499€</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <p style="text-align:center;font-size:12px;color:var(--text3);margin-top:16px">
      * Estimations basées sur les tarifs publics des principales plateformes juridiques en ligne. Annonces légales selon tarifs préfectoraux 2024.
    </p>
  </div>
</div>

<footer>
  © 2024 INPIrequest · Tous droits réservés ·
  <a href="#" style="color:var(--text2)">Mentions légales</a> ·
  <a href="#" style="color:var(--text2)">CGV</a>
</footer>
"""


# ──────────────────────────────────────────────────────────────────
# AUTH TEMPLATES
# ──────────────────────────────────────────────────────────────────

def auth_page(title, form_html, switch_html):
    return f"""
<div style="min-height:80vh;display:flex;align-items:center;justify-content:center;padding:40px 0">
  <div style="width:100%;max-width:440px">
    <div style="text-align:center;margin-bottom:32px">
      <div style="font-size:28px;font-weight:800;margin-bottom:8px">
        INPI<span style="color:var(--gold)">request</span>
      </div>
      <h1 style="font-size:24px;font-weight:700;margin-bottom:8px">{title}</h1>
    </div>
    <div class="card" style="padding:36px">
      {form_html}
    </div>
    <p style="text-align:center;margin-top:20px;color:var(--text2);font-size:14px">{switch_html}</p>
  </div>
</div>"""


# ──────────────────────────────────────────────────────────────────
# DISSOLUTION WIZARD
# ──────────────────────────────────────────────────────────────────

DISSOLUTION_HTML = """
<style>
.form-group{margin-bottom:20px}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:600px){.form-row{grid-template-columns:1fr}}
.recap-row{display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid var(--border);font-size:14px}
.recap-row:last-child{border:none}
.recap-label{color:var(--text2)}
.recap-val{font-weight:600;text-align:right;max-width:60%}
</style>

<div style="padding:60px 0 80px">
  <div style="text-align:center;margin-bottom:48px">
    <div style="font-size:13px;color:var(--gold);font-weight:600;margin-bottom:8px;letter-spacing:1px">DISSOLUTION & RADIATION</div>
    <h1 style="font-size:32px;font-weight:800;margin-bottom:10px">Fermer votre société</h1>
    <p style="color:var(--text2)">Remplissez le formulaire, on s'occupe du reste</p>
  </div>

  <div class="steps" id="steps">
    <div class="step active" id="s1"><div class="step-circle">1</div><div class="step-label">Société</div></div>
    <div class="step" id="s2"><div class="step-circle">2</div><div class="step-label">Dirigeants</div></div>
    <div class="step" id="s3"><div class="step-circle">3</div><div class="step-label">Liquidateur</div></div>
    <div class="step" id="s4"><div class="step-circle">4</div><div class="step-label">Récap</div></div>
  </div>

  <div style="max-width:660px;margin:0 auto">
    <form method="POST" id="disForm">
      <!-- STEP 1 -->
      <div class="step-panel active card" id="panel1">
        <h3 style="font-size:18px;font-weight:700;margin-bottom:24px">Informations de la société</h3>
        <div class="form-group">
          <label>Dénomination sociale *</label>
          <input type="text" name="nom_societe" placeholder="Ma Société SAS" required>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Numéro SIREN *</label>
            <input type="text" name="siren" placeholder="123 456 789" maxlength="11" required>
          </div>
          <div class="form-group">
            <label>Forme juridique *</label>
            <select name="forme">
              <option value="SAS">SAS</option>
              <option value="SARL">SARL</option>
              <option value="SCI">SCI</option>
              <option value="EURL">EURL</option>
              <option value="SA">SA</option>
              <option value="SASU">SASU</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label>Adresse du siège social *</label>
          <input type="text" name="adresse" placeholder="12 rue de la Paix, 75001 Paris" required>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Capital social (€) *</label>
            <input type="number" name="capital" placeholder="1000" min="1" required>
          </div>
          <div class="form-group">
            <label>Date de l'AGE *</label>
            <input type="date" name="date_age" required>
          </div>
        </div>
        <div style="display:flex;justify-content:flex-end;margin-top:8px">
          <button type="button" class="btn btn-gold" onclick="next(1)">Suivant →</button>
        </div>
      </div>

      <!-- STEP 2 -->
      <div class="step-panel card" id="panel2">
        <h3 style="font-size:18px;font-weight:700;margin-bottom:24px">Gérant & Associés</h3>
        <div class="form-row">
          <div class="form-group">
            <label>Prénom du gérant *</label>
            <input type="text" name="gerant_prenom" placeholder="Jean" required>
          </div>
          <div class="form-group">
            <label>Nom du gérant *</label>
            <input type="text" name="gerant_nom" placeholder="Dupont" required>
          </div>
        </div>
        <div class="form-group">
          <label>Adresse du gérant *</label>
          <input type="text" name="gerant_adresse" placeholder="5 avenue des Fleurs, 75008 Paris" required>
        </div>
        <div class="form-group">
          <label>Nombre d'associés</label>
          <select name="nb_associes">
            <option value="1">1 (société unipersonnelle)</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4 ou plus</option>
          </select>
        </div>
        <div class="form-group">
          <label>Montant du boni de liquidation (€) <span style="color:var(--text3)">(0 si aucun actif)</span></label>
          <input type="number" name="boni" placeholder="0" min="0" value="0">
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:8px">
          <button type="button" class="btn btn-outline" onclick="prev(2)">← Retour</button>
          <button type="button" class="btn btn-gold" onclick="next(2)">Suivant →</button>
        </div>
      </div>

      <!-- STEP 3 -->
      <div class="step-panel card" id="panel3">
        <h3 style="font-size:18px;font-weight:700;margin-bottom:8px">Liquidateur amiable</h3>
        <p style="color:var(--text2);font-size:14px;margin-bottom:24px">
          Le liquidateur est nommé pour gérer la clôture. Il peut être le gérant lui-même.
        </p>
        <div style="background:rgba(201,168,76,.08);border:1px solid rgba(201,168,76,.2);border-radius:10px;padding:14px 16px;margin-bottom:20px;font-size:13px;color:var(--gold)">
          💡 Par défaut, le gérant est nommé liquidateur. Vous pouvez changer si nécessaire.
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Prénom du liquidateur *</label>
            <input type="text" name="liq_prenom" placeholder="Jean" required>
          </div>
          <div class="form-group">
            <label>Nom du liquidateur *</label>
            <input type="text" name="liq_nom" placeholder="Dupont" required>
          </div>
        </div>
        <div class="form-group">
          <label>Adresse du liquidateur *</label>
          <input type="text" name="liq_adresse" placeholder="5 avenue des Fleurs, 75008 Paris" required>
        </div>
        <div class="form-group">
          <label>Email du liquidateur * <span style="color:var(--text3)">(pour la signature électronique)</span></label>
          <input type="email" name="liq_email" placeholder="liquidateur@email.com" required>
        </div>
        <div class="divider"></div>
        <h3 style="font-size:16px;font-weight:700;margin-bottom:16px">Documents à fournir</h3>
        <p style="color:var(--text2);font-size:14px;margin-bottom:16px">
          Ces documents sont fournis par votre comptable. Vous pourrez les uploader après le paiement.
        </p>
        <div style="display:flex;flex-direction:column;gap:10px">
          <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--card2);border-radius:10px;font-size:14px">
            <span>📊</span><span>Bilan de liquidation</span><span style="margin-left:auto;color:var(--text3);font-size:12px">À uploader</span>
          </div>
          <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--card2);border-radius:10px;font-size:14px">
            <span>🏦</span><span>Attestation fiscale (TVA + IS)</span><span style="margin-left:auto;color:var(--text3);font-size:12px">À uploader</span>
          </div>
          <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--card2);border-radius:10px;font-size:14px">
            <span>🛡️</span><span>Attestation de vigilance URSSAF</span><span style="margin-left:auto;color:var(--text3);font-size:12px">À uploader</span>
          </div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:24px">
          <button type="button" class="btn btn-outline" onclick="prev(3)">← Retour</button>
          <button type="button" class="btn btn-gold" onclick="showRecap()">Voir le récap →</button>
        </div>
      </div>

      <!-- STEP 4 RECAP -->
      <div class="step-panel card" id="panel4">
        <h3 style="font-size:18px;font-weight:700;margin-bottom:24px">Récapitulatif de votre dossier</h3>
        <div id="recap-content" style="margin-bottom:24px"></div>
        <div style="background:rgba(16,185,129,.08);border:1px solid rgba(16,185,129,.2);border-radius:12px;padding:16px;margin-bottom:24px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-weight:600">Total à payer</span>
            <span style="font-size:28px;font-weight:800;color:var(--green)">299€ TTC</span>
          </div>
          <p style="font-size:12px;color:var(--text2);margin-top:6px">Annonce légale + frais INPI + signature eIDAS inclus</p>
        </div>
        <input type="hidden" name="type" value="dissolution">
        <div style="display:flex;justify-content:space-between">
          <button type="button" class="btn btn-outline" onclick="prev(4)">← Modifier</button>
          <button type="submit" class="btn btn-gold" style="font-size:16px;padding:14px 32px">
            💳 Payer et démarrer
          </button>
        </div>
      </div>
    </form>
  </div>
</div>

<script>
let cur = 1;
const fields = {
  1: ['nom_societe','siren','adresse','capital','date_age'],
  2: ['gerant_prenom','gerant_nom','gerant_adresse'],
  3: ['liq_prenom','liq_nom','liq_adresse','liq_email']
};
function validate(step) {
  let ok = true;
  (fields[step] || []).forEach(n => {
    const el = document.querySelector(`[name="${n}"]`);
    if (el && !el.value.trim()) {
      el.style.borderColor = 'var(--red)';
      ok = false;
    } else if (el) el.style.borderColor = '';
  });
  return ok;
}
function go(from, to) {
  document.getElementById(`panel${from}`).classList.remove('active');
  document.getElementById(`panel${to}`).classList.add('active');
  document.getElementById(`s${from}`).classList.remove('active');
  document.getElementById(`s${from}`).classList.add('done');
  document.getElementById(`s${to}`).classList.add('active');
  cur = to;
  window.scrollTo({top:0,behavior:'smooth'});
}
function back(from, to) {
  document.getElementById(`panel${from}`).classList.remove('active');
  document.getElementById(`panel${to}`).classList.add('active');
  document.getElementById(`s${from}`).classList.remove('active');
  document.getElementById(`s${to}`).classList.remove('done');
  document.getElementById(`s${to}`).classList.add('active');
  cur = to;
  window.scrollTo({top:0,behavior:'smooth'});
}
function next(s) { if (validate(s)) go(s, s+1); }
function prev(s) { back(s, s-1); }
function showRecap() {
  if (!validate(3)) return;
  const get = n => document.querySelector(`[name="${n}"]`)?.value || '';
  const formes = {'SAS':'SAS','SARL':'SARL','SCI':'SCI','EURL':'EURL','SA':'SA','SASU':'SASU'};
  const forme = get('forme');
  const rows = [
    ['Société', get('nom_societe') + ' ' + forme],
    ['SIREN', get('siren')],
    ['Siège social', get('adresse')],
    ['Capital', get('capital') + ' €'],
    ['Date AGE', get('date_age')],
    ['Gérant', get('gerant_prenom') + ' ' + get('gerant_nom')],
    ['Liquidateur', get('liq_prenom') + ' ' + get('liq_nom')],
    ['Email liquidateur', get('liq_email')],
    ['Boni de liquidation', get('boni') + ' €'],
  ];
  document.getElementById('recap-content').innerHTML = rows.map(([l,v]) =>
    `<div class="recap-row"><span class="recap-label">${l}</span><span class="recap-val">${v}</span></div>`
  ).join('');
  go(3, 4);
}
</script>
"""


# ──────────────────────────────────────────────────────────────────
# CREATION WIZARD
# ──────────────────────────────────────────────────────────────────

CREATION_HTML = """
<style>
.type-card{
  border:2px solid var(--border);border-radius:14px;padding:24px;cursor:pointer;
  transition:.2s;text-align:center;background:var(--card)
}
.type-card:hover{border-color:rgba(59,130,246,.5);transform:translateY(-2px)}
.type-card.selected{border-color:var(--blue);background:rgba(59,130,246,.08)}
.type-card h3{font-size:20px;font-weight:800;margin-bottom:6px}
.type-card p{font-size:13px;color:var(--text2);line-height:1.5}
.type-badge{font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;
  background:rgba(59,130,246,.15);color:var(--blue);margin-bottom:12px;display:inline-block}
</style>

<div style="padding:60px 0 80px">
  <div style="text-align:center;margin-bottom:48px">
    <div style="font-size:13px;color:var(--blue);font-weight:600;margin-bottom:8px;letter-spacing:1px">CRÉATION DE SOCIÉTÉ</div>
    <h1 style="font-size:32px;font-weight:800;margin-bottom:10px">Créer votre société</h1>
    <p style="color:var(--text2)">Choisissez votre forme juridique et renseignez vos informations</p>
  </div>

  <div class="steps">
    <div class="step active" id="cs1"><div class="step-circle">1</div><div class="step-label">Type</div></div>
    <div class="step" id="cs2"><div class="step-circle">2</div><div class="step-label">Infos</div></div>
    <div class="step" id="cs3"><div class="step-circle">3</div><div class="step-label">Dirigeant</div></div>
    <div class="step" id="cs4"><div class="step-circle">4</div><div class="step-label">Récap</div></div>
  </div>

  <div style="max-width:700px;margin:0 auto">
    <form method="POST" id="creForm">

      <!-- STEP 1 : Type -->
      <div class="step-panel active" id="cpanel1">
        <div class="grid2" style="gap:16px;margin-bottom:24px">
          <div class="type-card" onclick="selectType('SAS',this)">
            <div class="type-badge">Recommandé</div>
            <h3>SAS</h3>
            <p>Société par Actions Simplifiée — flexible, idéale pour lever des fonds</p>
          </div>
          <div class="type-card" onclick="selectType('SARL',this)">
            <h3 style="margin-top:28px">SARL</h3>
            <p>Société à Responsabilité Limitée — classique, rassurante</p>
          </div>
          <div class="type-card" onclick="selectType('SASU',this)">
            <h3 style="margin-top:28px">SASU</h3>
            <p>SAS Unipersonnelle — 1 seul associé, idéale pour démarrer solo</p>
          </div>
          <div class="type-card" onclick="selectType('SCI',this)">
            <h3 style="margin-top:28px">SCI</h3>
            <p>Société Civile Immobilière — pour gérer un patrimoine immobilier</p>
          </div>
        </div>
        <input type="hidden" name="forme" id="forme_input" required>
        <div style="display:flex;justify-content:flex-end">
          <button type="button" class="btn" style="background:var(--blue);color:#fff" onclick="cnext(1)">Suivant →</button>
        </div>
      </div>

      <!-- STEP 2 : Infos -->
      <div class="step-panel card" id="cpanel2">
        <h3 style="font-size:18px;font-weight:700;margin-bottom:24px">Informations générales</h3>
        <div class="form-group">
          <label>Dénomination sociale *</label>
          <input type="text" name="nom_societe" placeholder="Ma Startup SAS" required>
        </div>
        <div class="form-group">
          <label>Objet social * <span style="color:var(--text3)">(activité principale)</span></label>
          <textarea name="objet" rows="3" placeholder="Développement et commercialisation de logiciels informatiques..." required style="resize:vertical"></textarea>
        </div>
        <div class="form-group">
          <label>Adresse du siège social *</label>
          <input type="text" name="adresse_siege" placeholder="12 rue de la Paix, 75001 Paris" required>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Capital social (€) *</label>
            <input type="number" name="capital" placeholder="1000" min="1" required>
          </div>
          <div class="form-group">
            <label>Date de début d'activité *</label>
            <input type="date" name="date_debut" required>
          </div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:8px">
          <button type="button" class="btn btn-outline" onclick="cprev(2)">← Retour</button>
          <button type="button" class="btn" style="background:var(--blue);color:#fff" onclick="cnext(2)">Suivant →</button>
        </div>
      </div>

      <!-- STEP 3 : Dirigeant -->
      <div class="step-panel card" id="cpanel3">
        <h3 style="font-size:18px;font-weight:700;margin-bottom:24px">Dirigeant & Associé principal</h3>
        <div class="form-row">
          <div class="form-group">
            <label>Prénom *</label>
            <input type="text" name="dir_prenom" placeholder="Jean" required>
          </div>
          <div class="form-group">
            <label>Nom *</label>
            <input type="text" name="dir_nom" placeholder="Dupont" required>
          </div>
        </div>
        <div class="form-group">
          <label>Date de naissance *</label>
          <input type="date" name="dir_naissance" required>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Nationalité *</label>
            <input type="text" name="dir_nationalite" placeholder="Française" required>
          </div>
          <div class="form-group">
            <label>% du capital *</label>
            <input type="number" name="dir_parts" placeholder="100" min="1" max="100" required>
          </div>
        </div>
        <div class="form-group">
          <label>Adresse *</label>
          <input type="text" name="dir_adresse" placeholder="5 avenue des Fleurs, 75008 Paris" required>
        </div>
        <div class="form-group">
          <label>Email * <span style="color:var(--text3)">(pour la signature électronique)</span></label>
          <input type="email" name="dir_email" placeholder="dirigeant@email.com" required>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:8px">
          <button type="button" class="btn btn-outline" onclick="cprev(3)">← Retour</button>
          <button type="button" class="btn" style="background:var(--blue);color:#fff" onclick="cshowRecap()">Voir le récap →</button>
        </div>
      </div>

      <!-- STEP 4 RECAP -->
      <div class="step-panel card" id="cpanel4">
        <h3 style="font-size:18px;font-weight:700;margin-bottom:24px">Récapitulatif</h3>
        <div id="crecap-content" style="margin-bottom:24px"></div>
        <div style="background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.2);border-radius:12px;padding:16px;margin-bottom:24px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-weight:600">Total à payer</span>
            <span style="font-size:28px;font-weight:800;color:var(--blue)">499€ TTC</span>
          </div>
          <p style="font-size:12px;color:var(--text2);margin-top:6px">Statuts + annonce légale + frais INPI + signature eIDAS inclus</p>
        </div>
        <input type="hidden" name="type" value="creation">
        <div style="display:flex;justify-content:space-between">
          <button type="button" class="btn btn-outline" onclick="cprev(4)">← Modifier</button>
          <button type="submit" class="btn" style="background:var(--blue);color:#fff;font-size:16px;padding:14px 32px">
            💳 Payer et créer
          </button>
        </div>
      </div>
    </form>
  </div>
</div>

<script>
let ctype = '';
function selectType(t, el) {
  document.querySelectorAll('.type-card').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
  ctype = t;
  document.getElementById('forme_input').value = t;
}
const cfields = {
  1: ['forme'],
  2: ['nom_societe','objet','adresse_siege','capital','date_debut'],
  3: ['dir_prenom','dir_nom','dir_naissance','dir_nationalite','dir_parts','dir_adresse','dir_email']
};
function cvalidate(s) {
  if (s === 1 && !ctype) { alert('Veuillez choisir une forme juridique'); return false; }
  let ok = true;
  (cfields[s] || []).forEach(n => {
    const el = document.querySelector(`[name="${n}"]`);
    if (el && !el.value.trim()) { el.style.borderColor='var(--red)'; ok=false; }
    else if (el) el.style.borderColor='';
  });
  return ok;
}
function cgo(f,t){
  document.getElementById(`cpanel${f}`).classList.remove('active');
  document.getElementById(`cpanel${t}`).classList.add('active');
  document.getElementById(`cs${f}`).classList.remove('active');
  document.getElementById(`cs${f}`).classList.add('done');
  document.getElementById(`cs${t}`).classList.add('active');
  window.scrollTo({top:0,behavior:'smooth'});
}
function cback(f,t){
  document.getElementById(`cpanel${f}`).classList.remove('active');
  document.getElementById(`cpanel${t}`).classList.add('active');
  document.getElementById(`cs${f}`).classList.remove('active');
  document.getElementById(`cs${t}`).classList.remove('done');
  document.getElementById(`cs${t}`).classList.add('active');
  window.scrollTo({top:0,behavior:'smooth'});
}
function cnext(s){ if(cvalidate(s)) cgo(s,s+1); }
function cprev(s){ cback(s,s-1); }
function cshowRecap(){
  if(!cvalidate(3)) return;
  const get = n => document.querySelector(`[name="${n}"]`)?.value || '';
  const rows = [
    ['Forme juridique', ctype],
    ['Société', get('nom_societe')],
    ['Objet social', get('objet').substring(0,60)+'...'],
    ['Siège social', get('adresse_siege')],
    ['Capital', get('capital') + ' €'],
    ['Début d\'activité', get('date_debut')],
    ['Dirigeant', get('dir_prenom') + ' ' + get('dir_nom')],
    ['Email dirigeant', get('dir_email')],
    ['Parts', get('dir_parts') + '%'],
  ];
  document.getElementById('crecap-content').innerHTML = rows.map(([l,v])=>
    `<div class="recap-row"><span class="recap-label">${l}</span><span class="recap-val">${v}</span></div>`
  ).join('');
  cgo(3,4);
}
</script>
"""


# ──────────────────────────────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────────────────────────────

def _phase_tracker(p):
    """Mini 3-step progress bar for dissolution dossiers (called with root P1)."""
    phases = [p] + sorted(p.children, key=lambda c: c.phase or 0)
    ph_labels = ["Dissolution", "Liquidation", "Clôture"]
    parts = []
    for i, (ph, pl) in enumerate(zip(phases, ph_labels)):
        ph_ico, _, ph_col = STATUS.get(ph.status, ("📝","","#94A3B8"))
        locked = ph.status == "en_attente"
        dot_col = "#475569" if locked else ph_col
        icon    = "🔒" if locked else ph_ico
        label_col = "var(--text3)" if locked else "var(--text2)"
        dot = (f'<a href="/procedure/{ph.id}" style="display:flex;flex-direction:column;'
               f'align-items:center;gap:3px;text-decoration:none;min-width:60px">'
               f'<div style="width:26px;height:26px;border-radius:50%;background:{dot_col}22;'
               f'border:2px solid {dot_col};display:flex;align-items:center;'
               f'justify-content:center;font-size:11px">{icon}</div>'
               f'<span style="font-size:10px;color:{label_col};white-space:nowrap">P{i+1} {pl}</span>'
               f'</a>')
        parts.append(dot)
        if i < len(phases) - 1:
            line_col = "#10B981" if phases[i].status == "termine" else "var(--border)"
            parts.append(f'<div style="flex:1;height:2px;background:{line_col};margin-bottom:13px"></div>')
    return ('<div style="display:flex;align-items:center;gap:0;margin-top:10px">'
            + "".join(parts) + "</div>")


def dashboard_html(user, procedures):
    nb_total    = len(procedures)
    nb_termine  = sum(1 for p in procedures if p.status == "termine")
    nb_en_cours = nb_total - nb_termine

    rows = ""
    for p in procedures:
        ico, lbl, col = STATUS.get(p.status, ("📝","En cours","#94A3B8"))
        typ_lbl = "Dissolution" if p.type == "dissolution" else "Création"
        typ_col = "#EF4444" if p.type == "dissolution" else "#3B82F6"
        date = p.created_at.strftime("%d/%m/%Y")
        tracker = _phase_tracker(p) if p.type == "dissolution" and p.phase == 1 else ""
        rows += f"""
        <div style="display:flex;align-items:center;gap:16px;padding:16px 20px;
             background:var(--card2);border-radius:12px;border:1px solid var(--border)">
          <div style="width:44px;height:44px;border-radius:10px;
               background:rgba(201,168,76,.1);display:flex;align-items:center;
               justify-content:center;font-size:20px">
            {"🏢" if p.type=="dissolution" else "🚀"}
          </div>
          <div style="flex:1;min-width:0">
            <div style="font-weight:600;font-size:15px;margin-bottom:3px">{p.societe or "—"}</div>
            <div style="font-size:12px;color:var(--text2)">{p.ref or "—"} · {date}</div>
            {tracker}
          </div>
          <span class="badge" style="background:rgba(0,0,0,.3);border:1px solid {typ_col}33;color:{typ_col}">{typ_lbl}</span>
          <span class="badge" style="background:rgba(0,0,0,.3);border:1px solid {col}33;color:{col}">{ico} {lbl}</span>
          <a href="/procedure/{p.id}" class="btn btn-ghost" style="padding:8px 16px;font-size:13px">Voir →</a>
        </div>"""

    if not rows:
        rows = """<div style="text-align:center;padding:60px 20px;color:var(--text2)">
          <div style="font-size:48px;margin-bottom:16px">📂</div>
          <p style="font-size:16px;margin-bottom:20px">Aucun dossier pour le moment</p>
          <div style="display:flex;gap:12px;justify-content:center">
            <a class="btn btn-gold" href="/dissolution">Fermer une société</a>
            <a class="btn btn-outline" href="/creation">Créer une société</a>
          </div>
        </div>"""

    return f"""
<div style="padding:48px 0">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:36px;flex-wrap:wrap;gap:16px">
    <div>
      <h1 style="font-size:28px;font-weight:800;margin-bottom:4px">Bonjour, {user.prenom} 👋</h1>
      <p style="color:var(--text2)">Suivez l'avancement de vos dossiers</p>
    </div>
    <div style="display:flex;gap:12px">
      <a class="btn btn-gold" href="/dissolution">+ Dissolution</a>
      <a class="btn btn-outline" href="/creation">+ Création</a>
    </div>
  </div>

  <div class="grid3" style="margin-bottom:36px">
    <div class="card stat">
      <div class="stat-val">{nb_total}</div>
      <div class="stat-lbl">Dossier(s) total</div>
    </div>
    <div class="card stat">
      <div class="stat-val" style="color:var(--orange)">{nb_en_cours}</div>
      <div class="stat-lbl">En cours</div>
    </div>
    <div class="card stat">
      <div class="stat-val" style="color:var(--green)">{nb_termine}</div>
      <div class="stat-lbl">Terminé(s)</div>
    </div>
  </div>

  <div class="card" style="padding:20px">
    <h2 style="font-size:16px;font-weight:700;margin-bottom:16px">Mes dossiers</h2>
    <div style="display:flex;flex-direction:column;gap:10px">{rows}</div>
  </div>
</div>"""


# ──────────────────────────────────────────────────────────────────
# PROCEDURE DETAIL
# ──────────────────────────────────────────────────────────────────

PHASE_META = {
    1: {
        "label": "Phase 1 — Dissolution",
        "desc":  "Convocation AGE · Annonce légale · Dépôt M2 au Guichet Unique",
        "docs": [
            ("PV AGE extraordinaire (dissolution)", "Modèle standardisé fourni", True),
            ("Formulaire M2", "Généré automatiquement", True),
            ("Mandat mandataire", "Généré automatiquement", True),
            ("Annonce légale de dissolution", "Commandée automatiquement", True),
        ],
        "timeline_done": ("✅","Terminé","Dissolution enregistrée à l'INPI"),
    },
    2: {
        "label": "Phase 2 — Liquidation",
        "desc":  "Opérations de liquidation · Documents comptables",
        "docs": [
            ("Rapport du liquidateur", "À rédiger par le liquidateur désigné", False),
            ("Bilan de liquidation", "À fournir par votre comptable", False),
            ("Attestation de régularité fiscale", "À obtenir auprès des impôts", False),
            ("Attestation URSSAF", "À fournir par votre comptable", False),
        ],
        "timeline_done": ("✅","Terminé","Liquidation terminée"),
    },
    3: {
        "label": "Phase 3 — Clôture & Radiation",
        "desc":  "Convocation AGE clôture · Annonce légale · Dépôt M4 · Radiation INPI",
        "docs": [
            ("PV AGE de clôture de liquidation", "Modèle standardisé fourni", True),
            ("Formulaire M4", "Généré automatiquement", True),
            ("Mandat mandataire", "Généré automatiquement", True),
            ("Annonce légale de clôture", "Commandée automatiquement", True),
        ],
        "timeline_done": ("✅","Terminé","Radiation enregistrée — Kbis de radiation disponible"),
    },
}


def _build_timeline(p, col):
    steps_order = ["formulaire","documents","signature","paiement","depose","termine"]
    cur_idx = steps_order.index(p.status) if p.status in steps_order else 0
    phase = p.phase
    done_label = PHASE_META[phase]["timeline_done"] if phase and phase in PHASE_META else ("✅","Terminé","Dossier terminé")
    labels = {
        "formulaire": ("📝","Formulaire reçu","Votre dossier a été créé"),
        "documents":  ("📄","Documents","En attente de vos documents"),
        "signature":  ("✍️","Signature","Documents envoyés pour signature eIDAS"),
        "paiement":   ("💳","Paiement","En attente de règlement"),
        "depose":     ("⚙️","Déposé à l'INPI","Dossier déposé sur le Guichet Unique"),
        "termine":    done_label,
    }
    timeline = ""
    for i, s in enumerate(steps_order):
        e, t, d = labels[s]
        done = i <= cur_idx
        c  = col if i == cur_idx else ("#10B981" if done else "var(--border)")
        tc = col if i == cur_idx else ("#10B981" if done else "var(--text3)")
        timeline += f"""
        <div style="display:flex;gap:16px;align-items:flex-start">
          <div style="display:flex;flex-direction:column;align-items:center;gap:4px">
            <div style="width:36px;height:36px;border-radius:50%;background:{c}22;
                 border:2px solid {c};display:flex;align-items:center;justify-content:center;
                 font-size:16px;flex-shrink:0">{e}</div>
            {"<div style='width:2px;flex:1;min-height:20px;background:var(--border)'></div>" if i < len(steps_order)-1 else ""}
          </div>
          <div style="padding-bottom:20px">
            <div style="font-weight:600;font-size:14px;color:{tc}">{t}</div>
            <div style="font-size:13px;color:var(--text2);margin-top:2px">{d}</div>
          </div>
        </div>"""
    return timeline


def _build_doc_rows(docs_needed):
    doc_rows = ""
    for name, origin, auto in docs_needed:
        icon  = "✅" if auto else "⏳"
        color = "var(--green)" if auto else "var(--orange)"
        doc_rows += f"""
        <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;
             background:var(--card2);border-radius:10px">
          <span style="font-size:18px">{icon}</span>
          <div style="flex:1">
            <div style="font-size:14px;font-weight:500">{name}</div>
            <div style="font-size:12px;color:var(--text2)">{origin}</div>
          </div>
          <span style="font-size:12px;color:{color};font-weight:600">
            {"Disponible" if auto else "En attente"}
          </span>
        </div>"""
    return doc_rows


def _phase_nav_bar(p):
    """Navigation between dissolution phases — returns HTML string."""
    root = p.parent if p.parent else p
    all_phases = [root] + sorted(root.children, key=lambda c: c.phase or 0)
    ph_names = {1: "Dissolution", 2: "Liquidation", 3: "Clôture"}
    nav_items = ""
    for ph in all_phases:
        ph_ico, _, ph_col = STATUS.get(ph.status, ("📝","","#94A3B8"))
        locked = ph.status == "en_attente"
        is_current = ph.id == p.id
        dot_col = "#475569" if locked else ph_col
        icon    = "🔒" if locked else ph_ico
        bg      = f"background:{dot_col}15;border:1px solid {dot_col}44;" if is_current else "border:1px solid transparent;"
        nav_items += (
            f'<a href="/procedure/{ph.id}" style="display:flex;align-items:center;gap:8px;'
            f'padding:8px 14px;border-radius:8px;text-decoration:none;{bg}'
            f'color:{"var(--gold)" if is_current else "var(--text2)"};font-size:13px;font-weight:{"700" if is_current else "400"}">'
            f'<span>{icon}</span>'
            f'<span>P{ph.phase} — {ph_names.get(ph.phase, "")}</span>'
            f'</a>'
        )
    return (
        '<div style="display:flex;gap:4px;background:var(--card2);border:1px solid var(--border);'
        'border-radius:10px;padding:4px;margin-bottom:28px;flex-wrap:wrap">'
        + nav_items + '</div>'
    )


def procedure_detail_html(p):
    ico, lbl, col = STATUS.get(p.status, ("📝","En cours","#94A3B8"))
    data = json.loads(p.data or "{}")

    # ── Dissolution avec phases ─────────────────────────────────────
    if p.type == "dissolution" and p.phase:
        meta = PHASE_META.get(p.phase, {})
        phase_label = meta.get("label", f"Phase {p.phase}")
        phase_desc  = meta.get("desc", "")
        docs_needed = meta.get("docs", [])

        phase_nav = _phase_nav_bar(p)

        if p.status == "en_attente":
            prev_phase = p.phase - 1
            locked_block = f"""
            <div style="text-align:center;padding:60px 20px">
              <div style="font-size:48px;margin-bottom:16px">🔒</div>
              <p style="font-size:16px;font-weight:600;margin-bottom:8px">Phase verrouillée</p>
              <p style="color:var(--text2);font-size:14px">
                Cette phase sera débloquée automatiquement une fois la
                <strong>Phase {prev_phase}</strong> marquée comme terminée.
              </p>
            </div>"""
            content_block = f"""
            <div class="grid2" style="align-items:start">
              <div class="card">{locked_block}</div>
              <div class="card">
                <h3 style="font-size:16px;font-weight:700;margin-bottom:16px">Documents de cette phase</h3>
                <div style="display:flex;flex-direction:column;gap:8px">
                  {_build_doc_rows(docs_needed)}
                </div>
              </div>
            </div>"""
        else:
            timeline = _build_timeline(p, col)
            doc_rows = _build_doc_rows(docs_needed)
            content_block = f"""
            <div class="grid2" style="align-items:start">
              <div class="card">
                <h3 style="font-size:16px;font-weight:700;margin-bottom:20px">Suivi</h3>
                {timeline}
              </div>
              <div class="card">
                <h3 style="font-size:16px;font-weight:700;margin-bottom:16px">Documents</h3>
                <div style="display:flex;flex-direction:column;gap:8px">{doc_rows}</div>
              </div>
            </div>"""

        return f"""
<div style="padding:48px 0 80px">
  <a href="/dashboard" style="color:var(--text2);font-size:14px;display:inline-flex;
     align-items:center;gap:6px;margin-bottom:28px">← Retour au dashboard</a>

  <div style="display:flex;align-items:flex-start;justify-content:space-between;
       flex-wrap:wrap;gap:20px;margin-bottom:24px">
    <div>
      <div style="font-size:13px;color:var(--text3);margin-bottom:4px">{p.ref or "—"}</div>
      <h1 style="font-size:26px;font-weight:800;margin-bottom:6px">{p.societe or "—"}</h1>
      <p style="font-size:13px;color:var(--text2);margin-bottom:8px">{phase_label} · {phase_desc}</p>
      <span class="badge" style="background:{col}22;border:1px solid {col}44;color:{col};font-size:13px">
        {ico} {lbl}
      </span>
    </div>
    <div class="card" style="padding:20px 28px;text-align:right;min-width:180px">
      <div style="font-size:12px;color:var(--text2);margin-bottom:4px">Prestation totale</div>
      <div style="font-weight:700;font-size:15px">Dissolution complète (3 phases)</div>
      <div style="font-size:24px;font-weight:800;color:var(--gold);margin-top:8px">
        {int(p.prix if p.phase == 1 else (p.parent.prix if p.parent else 0))}€
      </div>
    </div>
  </div>

  {phase_nav}
  {content_block}
</div>"""

    # ── Création (ou dissolution legacy sans phase) ─────────────────
    typ = "Création de société"
    timeline = _build_timeline(p, col)
    docs_needed = [
        ("Statuts de la société", "Modèle standardisé fourni", True),
        ("Formulaire M0", "Généré automatiquement", True),
        ("Mandat mandataire", "Généré automatiquement", True),
        ("Attestation de dépôt capital", "À fournir par votre banque", False),
        ("Annonce légale de constitution", "Commandée automatiquement", True),
    ]
    doc_rows = _build_doc_rows(docs_needed)

    return f"""
<div style="padding:48px 0 80px">
  <a href="/dashboard" style="color:var(--text2);font-size:14px;display:inline-flex;
     align-items:center;gap:6px;margin-bottom:32px">← Retour au dashboard</a>

  <div style="display:flex;align-items:flex-start;justify-content:space-between;
       flex-wrap:wrap;gap:20px;margin-bottom:36px">
    <div>
      <div style="font-size:13px;color:var(--text3);margin-bottom:4px">{p.ref or "—"}</div>
      <h1 style="font-size:28px;font-weight:800;margin-bottom:8px">{p.societe or "—"}</h1>
      <span class="badge" style="background:{col}22;border:1px solid {col}44;color:{col};font-size:13px">
        {ico} {lbl}
      </span>
    </div>
    <div class="card" style="padding:20px 28px;text-align:right;min-width:180px">
      <div style="font-size:12px;color:var(--text2);margin-bottom:4px">Service</div>
      <div style="font-weight:700;font-size:16px">{typ}</div>
      <div style="font-size:24px;font-weight:800;color:var(--gold);margin-top:8px">
        {int(p.prix)}€
      </div>
    </div>
  </div>

  <div class="grid2" style="align-items:start">
    <div class="card">
      <h3 style="font-size:16px;font-weight:700;margin-bottom:20px">Suivi du dossier</h3>
      {timeline}
    </div>
    <div class="card">
      <h3 style="font-size:16px;font-weight:700;margin-bottom:16px">Documents</h3>
      <div style="display:flex;flex-direction:column;gap:8px">{doc_rows}</div>
    </div>
  </div>
</div>"""


# ══════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════

@app.route("/")
def landing():
    return base("Accueil", LANDING)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        prenom = request.form.get("prenom","").strip()
        nom    = request.form.get("nom","").strip()
        email  = request.form.get("email","").strip().lower()
        pwd    = request.form.get("password","")
        if not all([prenom, nom, email, pwd]):
            flash("Tous les champs sont requis.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Un compte existe déjà avec cet email.", "error")
        elif len(pwd) < 6:
            flash("Le mot de passe doit faire au moins 6 caractères.", "error")
        else:
            u = User(prenom=prenom, nom=nom, email=email,
                     password=generate_password_hash(pwd))
            db.session.add(u)
            db.session.commit()
            session["user_id"] = u.id
            flash(f"Bienvenue {prenom} !", "success")
            return redirect(url_for("dashboard"))

    form = """
    <div class="form-group">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px">
        <div><label>Prénom</label><input name="prenom" placeholder="Jean" required></div>
        <div><label>Nom</label><input name="nom" placeholder="Dupont" required></div>
      </div>
    </div>
    <div class="form-group"><label>Email</label><input type="email" name="email" placeholder="jean@email.com" required></div>
    <div class="form-group"><label>Mot de passe</label><input type="password" name="password" placeholder="Min. 6 caractères" required></div>
    <button class="btn btn-gold" type="submit" style="width:100%;justify-content:center;margin-top:8px">
      Créer mon compte →
    </button>"""
    switch = f'Déjà un compte ? <a href="{url_for("login")}" style="color:var(--gold)">Se connecter</a>'
    return base("Créer un compte", auth_page("Créer un compte", form, switch))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        pwd   = request.form.get("password","")
        u = User.query.filter_by(email=email).first()
        if u and check_password_hash(u.password, pwd):
            session["user_id"] = u.id
            return redirect(url_for("dashboard"))
        flash("Email ou mot de passe incorrect.", "error")

    form = f"""
    <div class="form-group"><label>Email</label><input type="email" name="email" placeholder="jean@email.com" required></div>
    <div class="form-group"><label>Mot de passe</label><input type="password" name="password" placeholder="••••••••" required></div>
    <button class="btn btn-gold" type="submit" style="width:100%;justify-content:center;margin-top:8px">
      Se connecter →
    </button>"""
    switch = f'Pas encore de compte ? <a href="{url_for("register")}" style="color:var(--gold)">S\'inscrire</a>'
    return base("Connexion", auth_page("Connexion", form, switch))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/dashboard")
@login_required
def dashboard():
    u = get_user()
    # N'afficher que les procédures racines (pas les phases 2/3 qui sont des enfants)
    procs = Procedure.query.filter_by(user_id=u.id, parent_id=None).order_by(Procedure.created_at.desc()).all()
    return base("Dashboard", dashboard_html(u, procs), u)


@app.route("/dissolution", methods=["GET", "POST"])
@login_required
def dissolution():
    if request.method == "POST":
        u = get_user()
        nom = request.form.get("nom_societe","").strip()
        societe = f"{nom} {request.form.get('forme','')}".strip()
        data = json.dumps({k: v for k, v in request.form.items() if k != "type"})

        # Phase 1 — Dissolution (AG + annonce légale dissolution + dépôt M2)
        p1 = Procedure(
            user_id=u.id, type="dissolution", phase=1,
            societe=societe, status="documents", data=data,
            prix=PRIX["dissolution"]
        )
        db.session.add(p1)
        db.session.flush()
        p1.ref = make_ref("dissolution", p1.id, phase=1)

        # Phase 2 — Liquidation (période intermédiaire — débloquée après phase 1 terminée)
        p2 = Procedure(
            user_id=u.id, type="dissolution", phase=2,
            parent_id=p1.id, societe=societe, status="en_attente",
            data=data, prix=0
        )
        db.session.add(p2)
        db.session.flush()
        p2.ref = make_ref("dissolution", p2.id, phase=2)

        # Phase 3 — Clôture & Radiation (AG clôture + annonce légale clôture + dépôt M4)
        p3 = Procedure(
            user_id=u.id, type="dissolution", phase=3,
            parent_id=p1.id, societe=societe, status="en_attente",
            data=data, prix=0
        )
        db.session.add(p3)
        db.session.flush()
        p3.ref = make_ref("dissolution", p3.id, phase=3)

        db.session.commit()
        flash("Dossier créé en 3 phases ! Commencez par la Phase 1 — Dissolution.", "success")
        return redirect(url_for("procedure", id=p1.id))
    return base("Dissolution", DISSOLUTION_HTML)


@app.route("/creation", methods=["GET", "POST"])
@login_required
def creation():
    if request.method == "POST":
        u = get_user()
        nom = request.form.get("nom_societe","").strip()
        data = {k: v for k, v in request.form.items() if k != "type"}
        p = Procedure(
            user_id=u.id, type="creation",
            societe=f"{nom} {request.form.get('forme','')}".strip(),
            status="documents", data=json.dumps(data),
            prix=PRIX["creation"]
        )
        db.session.add(p)
        db.session.flush()
        p.ref = make_ref("creation", p.id)
        db.session.commit()
        flash("Dossier créé ! Vos modèles de statuts sont prêts à compléter.", "success")
        return redirect(url_for("procedure", id=p.id))
    return base("Création", CREATION_HTML)


@app.route("/procedure/<int:id>")
@login_required
def procedure(id):
    u = get_user()
    p = Procedure.query.filter_by(id=id, user_id=u.id).first_or_404()
    return base(f"Dossier {p.ref}", procedure_detail_html(p), u)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
