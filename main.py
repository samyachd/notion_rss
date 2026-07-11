import os
from dotenv import load_dotenv
from workflow import write_content, generate_synthese, decouper_synthese, create_page, envoyer_sur_page

# --- Configuration -----------------------------------------------------------
load_dotenv()

liste_de_sujets = [
    {
        "page_id": os.environ["NOTION_TECH_PAGE_ID"],
        "subject": "Tech",
        "flux": [
            "https://korben.info/feed",
            "https://www.numerama.com/feed/",
            "https://news.ycombinator.com/rss",
            "https://feeds.arstechnica.com/arstechnica/index"
        ]
    },
    {
        "page_id": os.environ["NOTION_ACTUALITES_PAGE_ID"],
        "subject": "Mondiales",
        "flux": [
            "https://www.france24.com/fr/rss",
            "https://www.monde-diplomatique.fr/rss/",
            "https://www.courrierinternational.com/feed/all/rss.xml",
            "https://www.lemonde.fr/rss/une.xml",
            
        ]
    }
]

def main():
    for sujet in liste_de_sujets:
        articles = write_content(sujet["flux"])
        if len(articles) > 0:
            synthese = generate_synthese(articles)
            liste_synthese = decouper_synthese(synthese)
            page_id = create_page(sujet["page_id"], sujet["subject"])
            envoyer_sur_page(liste_synthese,  page_id)
    return None

if __name__ == "__main__":
    main()