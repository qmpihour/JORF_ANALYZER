from flask import Flask, render_template_string, request, redirect, url_for
import spacy
import re
import os
import requests
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

# --- Initialisation Flask ---
app = Flask(__name__)

# --- Télécharger le modèle spaCy si besoin ---
import spacy.cli
spacy.cli.download("fr_core_news_md")

# --- Extraction classique du texte ---
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

# --- OCR fallback si texte vide ---
def ocr_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=300)
        img_path = f"page_{i}.png"
        pix.save(img_path)
        img = Image.open(img_path)
        text += pytesseract.image_to_string(img, lang="fra")
        os.remove(img_path)
    doc.close()
    return text

# --- Analyse NLP ---
def analyse_texte(texte):
    nlp = spacy.load("fr_core_news_md")
    doc = nlp(texte)

    personnalites = sorted(set(ent.text for ent in doc.ents if ent.label_ == "PER"))
    themes = ["agriculture", "numérique", "cybersécurité", "défense", "armée", "étranger", "coopération internationale"]
    themes_trouves = sorted({theme for theme in themes if re.search(rf"\b{theme}\b", texte, re.IGNORECASE)})
    nominations = [line.strip() for line in texte.split("\n") if re.search(r"nommée?|désignée?|relevée? de ses fonctions", line, re.IGNORECASE)]

    return personnalites, themes_trouves, nominations

# --- Template HTML ---
HTML_TEMPLATE = """
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="utf-8">
    <title>Dashboard JO</title>
    <style>
      body { font-family: sans-serif; margin: 2em; }
      h1 { color: #333; }
      ul { list-style: none; padding: 0; }
      li { margin-bottom: .5em; }
      .theme { background: #eee; display: inline-block; margin: 0.2em; padding: 0.2em 0.5em; border-radius: 5px; }
      form { margin-bottom: 2em; }
    </style>
  </head>
  <body>
    <h1>📰 Dashboard Journal Officiel</h1>
    <form method="POST" action="/analyse">
      <label for="url">Lien du PDF :</label>
      <input type="text" id="url" name="url" size="80" required>
      <button type="submit">Analyser</button>
    </form>

    {% if analysed %}
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
    {% endif %}
  </body>
</html>
"""

# --- Route principale ---
@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE, analysed=False)

# --- Route pour analyser un PDF ---
@app.route("/analyse", methods=["POST"])
def analyse():
    url = request.form["url"]
    response = requests.get(url)
    if response.status_code == 200:
        with open("jorf_temp.pdf", "wb") as f:
            f.write(response.content)
        print("✅ PDF téléchargé depuis :", url)

        texte = extract_text_from_pdf("jorf_temp.pdf")
        if not texte.strip():
            print("⚠️ Texte vide, fallback OCR…")
            texte = ocr_pdf("jorf_temp.pdf")
        else:
            print("✅ Texte extrait sans OCR.")

        personnalites, themes_trouves, nominations = analyse_texte(texte)
    else:
        personnalites, themes_trouves, nominations = [], [], []

    return render_template_string(HTML_TEMPLATE,
                                  analysed=True,
                                  personnalites=personnalites,
                                  nominations=nominations,
                                  themes=themes_trouves)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
