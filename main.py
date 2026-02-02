import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from atproto import Client, client_utils

# CONFIG
BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE")
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD")
PROMO_URL = "https://shop.canaries.co.uk/page/discountsandpromotions"
SEEN_FILE = "seen_promos.json"
KEYWORDS = ["FREE", "% OFF", "SALE", "OFFER", "DISCOUNT", "PRICE DROP", "CLEARANCE"]

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f, indent=2)

def setup_driver():
    """Sets up a headless Chrome driver optimized for GitHub Actions."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    # Mimic a real user to avoid bot detection
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # In Selenium 4.6+, we don't need ChromeDriverManager()
    return webdriver.Chrome(options=options)

def scrape_promos(driver):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🛍️ Accessing Norwich Shop...")
    driver.get(PROMO_URL)
    promos = []
    
    try:
        # Give the page 15 seconds to load the CMS content
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".cms-content")))
        
        # Pull text from headers and paragraphs
        elements = driver.find_elements(By.CSS_SELECTOR, ".cms-content h2, .cms-content h3, .cms-content p")
        
        for el in elements:
            text = el.text.strip()
            # Valid deals are usually substantial text blocks containing keywords
            if any(kw in text.upper() for kw in KEYWORDS):
                if 15 < len(text) < 500:
                    promos.append({"headline": text, "url": PROMO_URL})
        
        return promos
    except Exception as e:
        print(f"❌ Scraping Failed: {e}")
        raise e # Essential for the GitHub Action 'Retry' logic to work

def post_to_bluesky(promo, client):
    print(f"📤 Posting: {promo['headline'][:50]}...")
    tb = client_utils.TextBuilder()
    tb.text(f"🛍️ NCFC SHOP DEAL:\n\n{promo['headline']}\n\n")
    tb.link("View details here", promo['url'])
    tb.text("\n\n#NCFC #Canaries #OTBC")

    try:
        client.send_post(text=tb)
        return True
    except Exception as e:
        print(f"❌ Bluesky Error: {e}")
        return False

def main():
    # 1. Check Credentials
    if not BLUESKY_HANDLE or not BLUESKY_APP_PASSWORD:
        print("❌ Error: BLUESKY_HANDLE or BLUESKY_APP_PASSWORD not set in Environment.")
        return

    seen = load_seen()
    driver = None
    
    # 2. Scrape
    try:
        driver = setup_driver()
        found_promos = scrape_promos(driver)
    finally:
        if driver:
            driver.quit()

    # 3. Filter and Post
    new_promos = [p for p in found_promos if p["headline"] not in seen]
    
    if not new_promos:
        print("✅ Everything up to date. No new promos.")
        return

    try:
        client = Client()
        client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)
        
        # Post only the top match to avoid flooding the feed
        target = new_promos[0]
        if post_to_bluesky(target, client):
            seen.add(target["headline"])
            save_seen(seen)
            print("🎉 Success! Check your Bluesky feed.")
    except Exception as e:
        print(f"❌ Main Process Error: {e}")
        raise e

if __name__ == "__main__":
    main()
    
