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
SHOP_HOME = "https://shop.canaries.co.uk/"
IMAGE_PATH = "ncfcshop.png" 

def get_promotions():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "en-GB,en;q=0.9"
    }
    
    try:
        response = requests.get(PROM_URL, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # NEW LOGIC: Scan all text elements for high-value promo keywords
        potential_promos = []
        # We look for headers, bold text, and list items
        tags_to_check = soup.find_all(['h1', 'h2', 'h3', 'strong', 'li', 'p'])
        
        keywords = ["off", "%", "free", "sale", "printing", "discount", "offer"]

        for tag in tags_to_check:
            text = tag.get_text(" ", strip=True)
            # Only grab text that is meaningful (not too short, not a giant paragraph)
            if 10 < len(text) < 150:
                if any(word in text.lower() for word in keywords):
                    # Clean up double spaces or weird characters
                    clean_text = " ".join(text.split())
                    if clean_text not in potential_promos:
                        potential_promos.append(clean_text)

        # Remove duplicates and generic "Promotions" headers
        filtered_promos = [p for p in potential_promos if "discounts" not in p.lower() and "policy" not in p.lower()]

        if filtered_promos:
            # Join the best 3-4 promos with bullet points
            return "\n".join([f"• {p}" for p in filtered_promos[:4]])
        
        return "Flash offers are live! Check the site for 40% OFF Home Kit and more."

    except Exception as e:
        print(f"Scrape failed: {e}")
        return "New promotions available now at the Official Shop!"

def post_to_bluesky(promo_text):
    client = Client()
    client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

    # Image Handling
    thumb_blob = None
    if os.path.exists(IMAGE_PATH):
        try:
            with Image.open(IMAGE_PATH) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                thumb_blob = client.upload_blob(buffer.getvalue()).blob
        except Exception as e:
            print(f"Image error: {e}")

    # Text Construction with Facets (Blue Hashtags)
    tb = client_utils.TextBuilder()
    tb.text("🔰 Norwich City Shop Update\n\n")
    tb.text(f"{promo_text}\n\n")
    tb.tag("#NCFC", "NCFC")
    tb.text(" ")
    tb.tag("#OTBC", "OTBC")

    # Link Card Embed
    embed_external = models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            title="NCFC Shop Promotions",
            description="Official discounts on kits and training wear.",
            uri=SHOP_HOME,
            thumb=thumb_blob,
        )
    )

    client.send_post(text=tb, embed=embed_external)
    print("Post sent!")

if __name__ == "__main__":
    promo_data = get_promotions()
    post_to_bluesky(promo_data)
