from flask import Flask, render_template_string
import spacy
import re
import os

# Initialisation de l'app Flask
app = Flask(__name__)

# Chargement du modèle spaCy
nlp = spacy.load("fr_core_news_md")

# Lecture du texte du JO (remplace ce fichier par un autre si besoin)
with open("journal_officiel_sample.txt", "r", encoding="utf-8") as f:
    jo_text = f.read()

# Analyse NLP
doc = nlp(jo_text)

# Extraction des personnalités
personnalites = sorted(set(ent.text for ent in doc.ents if ent.label_ == "PER"))

# Détection des thèmes (exemple de liste modifiable)
themes = ["agriculture", "numérique", "cybersécurité", "défense", "armée", "étranger", "coopération internationale"]
themes_trouves = sorted({theme for theme in themes if re.search(rf"\b{theme}\b", jo_text, re.IGNORECASE)})

# Détection des nominations
nominations = []
for line in jo_text.split("\n"):
    if re.search(r"nommée?|désignée?|relevée? de ses fonctions", line, re.IGNORECASE):
        nominations.append(line.strip())

# Mini template HTML épuré
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

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, personnalites=personnalites, nominations=nominations, themes=themes_trouves)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)