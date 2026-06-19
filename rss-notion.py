"""
rss_vers_notion.py
------------------
Lit un ou plusieurs flux RSS et crée une page par article dans une base Notion.

Étape 1 du projet : la RÉCOLTE uniquement.
La synthèse (résumé) sera une étape séparée, ajoutée plus tard.

Avant de lancer :
1. pip install feedparser requests python-dotenv
2. Crée un fichier .env à côté de ce script avec :
       NOTION_TOKEN=ton_jeton_personnel
       NOTION_DATABASE_ID=l_id_de_ta_base
3. Vérifie que ta base Notion a bien les colonnes :
       Titre (titre), Lien (URL), Date (date), Source (texte)
"""

import os
import json
import time
from datetime import datetime

import feedparser
import requests
from dotenv import load_dotenv

# --- Configuration -----------------------------------------------------------

# Charge les variables du fichier .env (ton jeton et l'id de la base)
load_dotenv()

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

# Les flux que tu veux suivre. Ajoute autant d'URL que tu veux ici.
# Astuce : un subreddit s'écrit https://www.reddit.com/r/python.rss
FLUX = [
    "https://www.reddit.com/r/python.rss",
]

# Noms EXACTS des colonnes de ta base Notion (modifie si tu les as nommées autrement)
COL_TITRE = "Titre"
COL_LIEN = "Lien"
COL_DATE = "Date"
COL_SOURCE = "Source"

# Fichier local qui mémorise les liens déjà envoyés, pour ne pas créer de doublons
FICHIER_DEJA_VUS = "deja_vus.json"

# En-têtes communs à toutes les requêtes vers l'API Notion
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


# --- Gestion des doublons ----------------------------------------------------

def charger_deja_vus():
    """Renvoie l'ensemble des liens déjà traités lors des exécutions précédentes."""
    if os.path.exists(FICHIER_DEJA_VUS):
        with open(FICHIER_DEJA_VUS, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def sauvegarder_deja_vus(liens):
    """Écrit l'ensemble des liens connus dans le fichier local."""
    with open(FICHIER_DEJA_VUS, "w", encoding="utf-8") as f:
        json.dump(sorted(liens), f, ensure_ascii=False, indent=2)


# --- Écriture dans Notion ----------------------------------------------------

def creer_page(titre, lien, date_iso, source):
    """Crée une page (= une ligne) dans la base Notion pour un article."""
    proprietes = {
        COL_TITRE: {"title": [{"text": {"content": titre}}]},
        COL_LIEN: {"url": lien},
        COL_SOURCE: {"rich_text": [{"text": {"content": source}}]},
    }
    # La date n'est ajoutée que si l'article en fournit une
    if date_iso:
        proprietes[COL_DATE] = {"date": {"start": date_iso}}

    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": proprietes,
    }

    reponse = requests.post(
        "https://api.notion.com/v1/pages",
        headers=HEADERS,
        json=payload,
    )

    # On signale clairement si Notion refuse la requête
    if reponse.status_code != 200:
        print(f"  ⚠ Erreur Notion ({reponse.status_code}) : {reponse.text}")
        return False
    return True


def date_en_iso(article):
    """Transforme la date d'un article RSS en format ISO, ou None si absente."""
    if getattr(article, "published_parsed", None):
        return datetime(*article.published_parsed[:6]).isoformat()
    return None


# --- Programme principal -----------------------------------------------------

def main():
    deja_vus = charger_deja_vus()
    nb_ajoutes = 0

    for url_flux in FLUX:
        print(f"Lecture du flux : {url_flux}")
        flux = feedparser.parse(url_flux)
        nom_source = flux.feed.get("title", url_flux)

        for article in flux.entries:
            lien = article.get("link")
            titre = article.get("title", "(sans titre)")

            # On saute les articles déjà envoyés une fois
            if not lien or lien in deja_vus:
                continue

            ok = creer_page(titre, lien, date_en_iso(article), nom_source)
            if ok:
                deja_vus.add(lien)
                nb_ajoutes += 1
                print(f"  + {titre}")

            # On respecte la limite de l'API Notion (max 3 requêtes/seconde)
            time.sleep(0.35)

    sauvegarder_deja_vus(deja_vus)
    print(f"\nTerminé : {nb_ajoutes} nouvel(s) article(s) ajouté(s) dans Notion.")


if __name__ == "__main__":
    main()