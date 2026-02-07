import os
import requests
from bs4 import BeautifulSoup
from atproto import Client, client_utils, models
from io import BytesIO
from PIL import Image

# CONFIG
BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE")
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD")
PROM_URL = "https://shop.canaries.co.uk/page/discountsandpromotions"
IMAGE_PATH = "ncfcshop.png"

def get_promotions():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(PROM_URL, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # TARGETED SCRAPING: Find the specific container for promotions
        # We search for the anchor/div that contains the 'promotions' ID
        promo_section = soup.find(id='promotions') or soup.find('a', {'name': 'promotions'})
        
        # If the ID isn't a container, we look at the parent or next sibling elements
        container = promo_section.find_parent('div') if promo_section else soup.find('div', class_='page-body')

        promos = []
        # We only want list items (li) or bold text (strong) inside this specific area
        for item in container.find_all(['li', 'strong', 'h3']):
            text = item.get_text(strip=True)
            
            # Validation: Must contain deal-related keywords
            if any(word in text.lower() for word in ["off", "%", "free", "discount", "printing"]):
                # Clean out generic navigation text that might have slipped in
                if "Licensed Products" not in text and text not in promos:
                    promos.append(text)
        
        if promos:
            return "\n".join([f"• {p}" for p in promos[:4]])
        
        return "New promotions are live! Visit the shop for 40% OFF and more."

    except Exception as e:
        print(f"Scrape error: {e}")
        return "Check out the latest offers at the Norwich City Shop!"

def post_to_bluesky(promo_text):
    client = Client()
    client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

    # Image Handling
    thumb_blob = None
    if os.path.exists(IMAGE_PATH):
        with Image.open(IMAGE_PATH) as img:
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            thumb_blob = client.upload_blob(buffer.getvalue()).blob

    # Text Construction with Blue Clickable Hashtag
    tb = client_utils.TextBuilder()
    tb.text("🔰 Norwich City Shop Promotions\n\n")
    tb.text(f"{promo_text}\n\n")
    tb.tag("#NCFC", "NCFC") # This creates the 'Facet' for the blue link

    # Link Card
    embed_external = models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            title="NCFC Official Shop Offers",
            description="View current discounts and kits.",
            uri=PROM_URL,
            thumb=thumb_blob,
        )
    )

    client.send_post(text=tb, embed=embed_external)
    print("Successfully posted to Bluesky!")

if __name__ == "__main__":
    promo_data = get_promotions()
    post_to_bluesky(promo_data)
