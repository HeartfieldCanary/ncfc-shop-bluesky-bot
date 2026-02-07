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
        
        # We only want the bold titles or headings
        # These usually contain the "40% Off" or "Free Printing" headlines
        potential_deals = soup.find_all(['h3', 'strong', 'h2'])
        
        extracted_deals = []
        for item in potential_deals:
            text = item.get_text(strip=True)
            
            # CRITERIA:
            # 1. Must contain a 'deal' keyword
            # 2. Must be short (Headlines are short, T&Cs are long)
            # 3. Must not be the boring membership/season ticket stuff
            keywords = ["off", "%", "free", "sale", "printing", "reduction"]
            is_deal = any(k in text.lower() for k in keywords)
            is_short = len(text) < 60  # Promotion titles are rarely longer than this
            is_not_generic = not any(x in text.lower() for x in ["season ticket", "membership", "unique", "entitles"])

            if is_deal and is_short and is_not_not_generic:
                if text not in extracted_deals:
                    extracted_deals.append(text)

        if extracted_deals:
            # Sort to make sure "40% Off" or "Sale" comes first if found
            extracted_deals.sort(key=lambda x: ("%" in x or "Off" in x), reverse=True)
            return "\n".join([f"• {d}" for d in extracted_deals[:4]])
        
        return "• 40% Off All Replica Home Kit\n• Free TOURE 37 or FIELD 26 Printing"

    except Exception as e:
        print(f"Scrape error: {e}")
        return "New offers available at the NCFC Shop!"

def post_to_bluesky(promo_text):
    client = Client()
    client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

    thumb_blob = None
    if os.path.exists(IMAGE_PATH):
        with Image.open(IMAGE_PATH) as img:
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=80)
            thumb_blob = client.upload_blob(buffer.getvalue()).blob

    tb = client_utils.TextBuilder()
    tb.text("🔰 Norwich City Shop Promotions\n\n")
    
    # Final safety check: Bluesky limit is 300. 
    # We truncate the middle if it's somehow still too long.
    clean_text = promo_text if len(promo_text) < 220 else promo_text[:217] + "..."
    
    tb.text(f"{clean_text}\n\n")
    tb.tag("#NCFC", "NCFC")
    tb.text(" ")
    tb.tag("#OTBC", "OTBC")

    embed_external = models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            title="NCFC Shop Offers",
            description="View the latest discounts and promotions.",
            uri=PROM_URL,
            thumb=thumb_blob,
        )
    )

    client.send_post(text=tb, embed=embed_external)
    print("Post Successful!")

if __name__ == "__main__":
    deals = get_promotions()
    post_to_bluesky(deals)
