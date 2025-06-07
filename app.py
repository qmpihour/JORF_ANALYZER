from flask import Flask, render_template_string
import spacy
import re
import os
import requests
import fitz  # PyMuPDF
import datetime

# --- Initialisation Flask ---
app = Flask(__name__)

# --- Télécharger le modèle spaCy si besoin ---
import spacy.cli
spacy.cli.download("fr_core_news_md")

# --- Fonction pour télécharger le JORF du jour ---
def download_jorf_pdf():
    today = datetime.date.today()
    date_str = today.strftime("%Y%m%d")
    url = f"https://www.legifrance.gouv.fr/download/pdf/jorf/jorf_{date_str}.pdf"
    response = requests.get(url)
    if response.status_code == 200:
        with open("jorf_du_jour.pdf", "wb") as f:
            f.write(response.content)
        print("✅ JORF téléchargé :", url)
        return True
    else:
        print("❌ Échec du téléchargement :", response.status_code)
        return False

# --- Fonction pour extraire le texte du PDF ---
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

# --- Fonction pour analyser le texte ---
def analyse_texte(texte):
    nlp = spacy.load("fr_core_news_md")
    doc = nlp(texte)

    # Personnalités
    personnalites = sorted(set(ent.text for ent in doc.ents if ent.label_ == "PER"))

    # Thématiques
    themes = ["agriculture", "numérique", "cybersécurité", "défense", "armée", "étranger", "coopération internationale"]
    themes_trouves = sorted({theme for theme in themes if re.search(rf"\b{theme}\b", texte, re.IGNORECASE)})

    # Nominations
    nominations = []
    for line in texte.split("\n"):
        if re.search(r"nommée?|désignée?|relevée? de ses fonctions", line, re.IGNORECASE):
            nominations.append(line.strip())

    return personnalites, themes_trouves, nominations

# --- Mini template HTML ---
HTML_TEMPLATE = """
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="utf-8">
    <title>Dashboard JO</title>
    <style>
      body { font-family: sans-serif; margin: 2em; }
      h2 { color: #333; }
      ul { list-style: none; padding: 0; }
      li { margin-bottom: .5em; }
      .theme { background: #eee; display: inline-block; margin: 0.2em; padding: 0.2em 0.5em; border-radius: 5px; }
    </style>
  </head>
  <body>
    <h1>📰 Dashboard Journal Officiel</h1>
    <h2>📛 Personnalités détectées :</h2>
    <ul>
      {% for p in personnalites %}
        <li>{{ p }}</li>
      {% endfor %}
    </ul>
    <h2>🏛️ Nominations détectées :</h2>
    <ul>
      {% for n in nominations %}
        <li>{{ n }}</li>
      {% endfor %}
    </ul>
    <h2>📃 Thèmes repérés :</h2>
    <div>
      {% for t in themes %}
        <span class="theme">{{ t }}</span>
      {% endfor %}
    </div>
  </body>
</html>
"""

# --- Route principale ---
@app.route("/")
def index():
    if download_jorf_pdf():
        texte_jorf = extract_text_from_pdf("jorf_du_jour.pdf")
    else:
        texte_jorf = "Aucun JORF disponible aujourd'hui."

    personnalites, themes_trouves, nominations = analyse_texte(texte_jorf)

    return render_template_string(HTML_TEMPLATE,
                                  personnalites=personnalites,
                                  nominations=nominations,
                                  themes=themes_trouves)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
