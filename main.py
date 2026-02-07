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
        
        # Look for the promotions anchor
        promo_start = soup.find('a', {'name': 'promotions'}) or soup.find(id='promotions')
        
        extracted_deals = []
        if promo_start:
            # Check elements following the anchor
            for sibling in promo_start.find_all_next(['h3', 'strong', 'li']):
                text = sibling.get_text(strip=True)
                
                # We want specific "Flash" deals, not general membership rules
                if any(key in text.lower() for key in ["off", "%", "free", "sale", "printing"]):
                    # Ignore the long membership/generic text
                    if "Season Ticket" not in text and "unique discount" not in text:
                        if text not in extracted_deals and len(text) > 5:
                            extracted_deals.append(text)
                
                if len(extracted_deals) >= 3: break # Keep it short to stay under 300 chars

        if extracted_deals:
            return "\n".join([f"• {d}" for d in extracted_deals])
        
        # Safe fallback if scraping fails
        return "• 40% Off All Replica Home Kit\n• Free TOURE 37 or FIELD 26 Printing"

    except Exception as e:
        print(f"Scrape error: {e}")
        return "Check the shop for the latest promotions!"

def post_to_bluesky(promo_text):
    client = Client()
    client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

    # Image Processing
    thumb_blob = None
    if os.path.exists(IMAGE_PATH):
        with Image.open(IMAGE_PATH) as img:
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=80)
            thumb_blob = client.upload_blob(buffer.getvalue()).blob

    # Build post with character safety
    tb = client_utils.TextBuilder()
    tb.text("🔰 Norwich City Shop Promotions\n\n")
    
    # Logic to ensure we don't exceed 300 characters
    # Header (~35) + Hashtag (~10) leaves ~250 for deals
    if len(promo_text) > 240:
        promo_text = promo_text[:237] + "..."
    
    tb.text(f"{promo_text}\n\n")
    tb.tag("#NCFC", "NCFC") # Blue clickable hashtag

    # Embed Link Card
    embed_external = models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            title="NCFC Shop Offers",
            description="Official discounts and shirt printing.",
            uri=PROM_URL,
            thumb=thumb_blob,
        )
    )

    # Final send
    client.send_post(text=tb, embed=embed_external)
    print("Post Successful!")

if __name__ == "__main__":
    deals = get_promotions()
    post_to_bluesky(deals)
