import os
from datetime import datetime
import feedparser
from pathlib import Path
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from notion_client import Client
from dotenv import load_dotenv

# --- Configuration -----------------------------------------------------------
load_dotenv()

notion = Client(auth=os.environ["NOTION_TOKEN"])
client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            initial_delay=1.0,
            attempts=10,
            http_status_codes=[408, 429, 500, 502, 503, 504],
        ),
        timeout=120 * 1000,
    ),
)
DAY = datetime.now().strftime("%Y-%m-%d")

# --- Gestion des doublons ----------------------------------------------------

def nettoyer_html(texte):
    if not texte:
        return ""
    sans_html = BeautifulSoup(texte, "html.parser").get_text(separator=" ").strip()
    return " ".join(sans_html.split())  # Supprime les espaces multiples

# --- Lecture des flux RSS -----------------------------------------------------

def write_content(list_flux):
    articles = []
    nb_ajoutes = 0

    for url_flux in list_flux:
        print(f"Lecture du flux : {url_flux}")
        flux = feedparser.parse(url_flux)
        nom_source = flux.feed.get("title", url_flux)

        for article in flux.entries:
            if article.get("content"):
                content = nettoyer_html(article.get("content")[0].get("value"))
            elif article.get("summary"):
                content = nettoyer_html(article.get("summary"))
            elif article.get("description"):
                content = nettoyer_html(article.get("description"))
            else :
                content = "(aucun contenu disponible)"
            titre = article.get("title", "(sans titre)")
            articles.append({
                "content": content, 
                "title": titre, 
                "source": nom_source})
            nb_ajoutes += 1
            print(f"Ajoutés + {titre}")
            print(f"{nb_ajoutes} articles ajoutés au total.")
    return articles

def generate_synthese(content):
    reponse = client.models.generate_content(
        model="gemini-3.5-flash",
        config=types.GenerateContentConfig(
            temperature=0.5,
            system_instruction="""Tu es un assistant qui résume des articles.
            Mets moi uniquement les news du jour, en français, sous forme de synthèse.
            Renvoies un simple résumé en texte brut, sans mise en forme, sans balises HTML, sans emojis, sans hashtags."""
        ),
        contents=[
            {
                "role": "user",
                "parts": [{"text": f"Voici les articles à résumer : {content}"}]
            }
        ]
    )
    return reponse.text

def create_page(notion_page_id, subject):
    nouvelle_page = notion.pages.create(
        parent={"page_id": notion_page_id},
        position={"type": "page_start"},
        properties={
            "title": {"title": [{"text": {"content": f"Synthèse actualités {subject} du {DAY}"}}]}
        },
        children=[
            {
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"text": {"content": f"Synthèse actualités {subject} du {DAY}"}}]},
            },
        ],
    )

    print("Page créée :", nouvelle_page["id"])
    return nouvelle_page["id"]

def decouper_synthese(synthese):
    liste_synthese = []
    while len(synthese) > 2000:
        saut = synthese.rfind("\n", 0, 2000)
        if saut == -1:
            espace = synthese.rfind(" ", 0, 2000)
            if espace == -1:
                espace = 2000
                liste_synthese.append(synthese[0:espace])
                synthese = synthese[espace:]
            else:
                liste_synthese.append(synthese[0:espace])
                synthese = synthese[espace+1:]
        else:
            liste_synthese.append(synthese[0:saut])
            synthese = synthese[saut+1:]
    liste_synthese.append(synthese)
    return liste_synthese

def envoyer_sur_page(liste_synthese, page_id):
    for synthese in liste_synthese:
        notion.blocks.children.append(
                page_id,
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"text": {"content": f"{synthese}"}}]},
                    },
                ],
            )

    print("Synthèse envoyée sur la page Notion :", page_id)
    return None