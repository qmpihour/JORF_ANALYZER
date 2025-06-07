from flask import Flask, render_template_string
import spacy
import re
import os
import requests
import fitz  # PyMuPDF
import datetime
from PIL import Image
import pytesseract

# --- Initialisation Flask ---
app = Flask(__name__)

# --- Télécharger le modèle spaCy si besoin ---
import spacy.cli
spacy.cli.download("fr_core_news_md")

# --- Fonction pour télécharger le JORF du jour ---
def download_jorf_pdf():
    today = datetime.date.today() - datetime.timedelta(days=1)
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

# --- Extraction du texte classique ---
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
        pix = page.get_pixmap(dpi=300)  # haute résolution
        img_path = f"page_{i}.png"
        pix.save(img_path)
        img = Image.open(img_path)
        text += pytesseract.image_to_string(img, lang="fra")  # lang=fra pour le français
        os.remove(img_path)
    doc.close()
    return text

# --- Fonction d'analyse NLP ---
def analyse_texte(texte):
    nlp = spacy.load("fr_core_news_md")
    doc = nlp(texte)

    personnalites = sorted(set(ent.text for ent in doc.ents if ent.label_ == "PER"))
    themes = ["agriculture", "numérique", "cybersécurité", "défense", "armée", "étranger", "coopération internationale"]
    themes_trouves = sorted({theme for theme in themes if re.search(rf"\b{theme}\b", texte, re.IGNORECASE)})
    nominations = [line.strip() for line in texte.split("\n") if re.search(r"nommée?|désignée?|relevée? de ses fonctions", line, re.IGNORECASE)]

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

@app.route("/")
def index():
    if download_jorf_pdf():
        texte_jorf = extract_text_from_pdf("jorf_du_jour.pdf")
        if not texte_jorf.strip():
            print("⚠️ Texte vide, fallback OCR…")
            texte_jorf = ocr_pdf("jorf_du_jour.pdf")
        else:
            print("✅ Texte extrait sans OCR.")
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
