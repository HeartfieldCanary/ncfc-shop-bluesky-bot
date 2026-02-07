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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(PROM_URL, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Locate the specific 'Promotions' header
        # The site uses an anchor with name="promotions" right before the good stuff
        promo_start = soup.find('a', {'name': 'promotions'}) or soup.find(id='promotions')
        
        extracted_deals = []
        
        if promo_start:
            # Look at everything AFTER the 'Promotions' header until the end of the content
            current_node = promo_start
            while current_node:
                current_node = current_node.next_element
                if not current_node: break
                
                # We want text from headers (h3) and strong tags which usually hold the deal titles
                if current_node.name in ['h3', 'strong', 'p']:
                    text = current_node.get_text(strip=True)
                    
                    # Look for the actual "meat" of the deal
                    if any(key in text.lower() for key in ["off", "%", "free", "sale", "2 for"]):
                        # FILTER: Skip the generic membership terms we already know
                        if "Season Ticket" not in text and "valid one time only" not in text:
                            if text not in extracted_deals:
                                extracted_deals.append(text)
                
                # Stop if we hit the footer or a completely different section
                if len(extracted_deals) >= 5: break

        if extracted_deals:
            return "\n".join([f"• {d}" for d in extracted_deals[:3]])
        
        # Fallback if the site layout changed slightly
        return "• 40% Off 2025/26 Home Replica Kit\n• Free TOURE 37 Shirt Printing\n• Final Reductions: Up to 70% Off"

    except Exception as e:
        print(f"Scrape error: {e}")
        return "New offers are live! Visit the shop for the latest kit deals."

def post_to_bluesky(promo_text):
    client = Client()
    client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

    # Image logic
    thumb_blob = None
    if os.path.exists(IMAGE_PATH):
        with Image.open(IMAGE_PATH) as img:
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            thumb_blob = client.upload_blob(buffer.getvalue()).blob

    tb = client_utils.TextBuilder()
    tb.text("🔰 NCFC Shop: Live Promotions\n\n")
    tb.text(f"{promo_text}\n\n")
    tb.tag("#NCFC", "NCFC")
    tb.text(" ")
    tb.tag("#OTBC", "OTBC")

    embed_external = models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            title="NCFC Shop Discounts",
            description="Official replica kits and training wear deals.",
            uri=PROM_URL,
            thumb=thumb_blob,
        )
    )

    client.send_post(text=tb, embed=embed_external)
    print("Post Successful!")

if __name__ == "__main__":
    deals = get_promotions()
    post_to_bluesky(deals)
