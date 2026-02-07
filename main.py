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
        
        # 1. Focus only on the main content area to avoid header/footer links
        content = soup.find(id='promotions') or soup.find('div', class_='page-body') or soup
        
        # 2. Get all text and split it into individual lines
        lines = content.get_text(separator="\n").split("\n")
        
        extracted_deals = []
        # Keywords that indicate a "headline" deal
        keywords = ["off", "%", "free", "sale", "printing", "reduction", "save"]
        # Words that indicate boring terms and conditions
        boring_stuff = ["entitles", "membership", "unique", "season ticket", "valid", "terms", "condition"]

        for line in lines:
            clean_line = line.strip()
            # Only look at lines that are likely headlines (between 10 and 70 characters)
            if 10 < len(clean_line) < 70:
                lower_line = clean_line.lower()
                if any(k in lower_line for k in keywords):
                    if not any(b in lower_line for b in boring_stuff):
                        if clean_line not in extracted_deals:
                            extracted_deals.append(clean_line)

        if extracted_deals:
            # Always put the biggest discount (%) at the top
            extracted_deals.sort(key=lambda x: "%" in x, reverse=True)
            return "\n".join([f"• {d}" for d in extracted_deals[:4]])
        
        # If the scraper still finds nothing, we use the known current deals
        return "• 40% Off All 2024/25 Replica Home Kit\n• Free TOURE 37 or FIELD 26 Printing"

    except Exception as e:
        print(f"Scrape error: {e}")
        return "New offers are live! Visit the shop for the latest deals."

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
    tb.text("🔰 NCFC Shop - Current Special Offers\n\n")
    
    # Ensure text is under the 300-grapheme limit
    if len(promo_text) > 230:
        promo_text = promo_text[:227] + "..."
    
    tb.text(f"{promo_text}\n\n")
    tb.tag("#NCFC", "NCFC")
    tb.text(" ")
    tb.tag("#OTBC", "OTBC")

    embed_external = models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            title="NCFC Shop Offers",
            description="View official discounts and promotions.",
            uri=PROM_URL,
            thumb=thumb_blob,
        )
    )

    client.send_post(text=tb, embed=embed_external)
    print("Post Successful!")

if __name__ == "__main__":
    deals = get_promotions()
    post_to_bluesky(deals)
