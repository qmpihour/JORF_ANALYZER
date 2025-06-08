from flask import Flask, render_template_string, request, redirect
import spacy
import re
import os
import requests
import feedparser
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

app = Flask(__name__)

# --- Télécharger le modèle spaCy si besoin ---
import spacy.cli
spacy.cli.download("fr_core_news_md")

# --- OCR fallback ---
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

# --- Extraction classique ---
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
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

# --- Fonction pour télécharger le PDF du jour via le flux RSS ---
def download_latest_jorf_pdf():
    RSS_URL = "https://www.legifrance.gouv.fr/rss/jorf.xml"
    feed = feedparser.parse(RSS_URL)
    latest_entry = feed.entries[0]

    print("🔎 Récupération de la page HTML :", latest_entry.link)
    response = requests.get(latest_entry.link)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        pdf_link = None

        for a_tag in soup.find_all("a", href=True):
            if a_tag["href"].endswith(".pdf"):
                pdf_link = a_tag["href"]
                break

        if pdf_link:
            if not pdf_link.startswith("http"):
                pdf_link = "https://www.legifrance.gouv.fr" + pdf_link
            print("✅ Lien PDF trouvé :", pdf_link)

            pdf_response = requests.get(pdf_link)
            if pdf_response.status_code == 200:
                with open("jorf_du_jour.pdf", "wb") as f:
                    f.write(pdf_response.content)
                print("✅ PDF téléchargé.")
                return True
            else:
                print("❌ Échec téléchargement PDF :", pdf_response.status_code)
                return False
        else:
            print("❌ Aucun lien PDF trouvé.")
            return False
    else:
        print("❌ Échec de la récupération HTML :", response.status_code)
        return False

# --- Mini template HTML ---
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
      <button type="submit">Analyser le JO du jour</button>
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

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE, analysed=False)

@app.route("/analyse", methods=["POST"])
def analyse():
    if download_latest_jorf_pdf():
        texte_jorf = extract_text_from_pdf("jorf_du_jour.pdf")
        if not texte_jorf.strip():
            print("⚠️ Texte vide, fallback OCR…")
            texte_jorf = ocr_pdf("jorf_du_jour.pdf")
        else:
            print("✅ Texte extrait sans OCR.")
        personnalites, themes_trouves, nominations = analyse_texte(texte_jorf)
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
