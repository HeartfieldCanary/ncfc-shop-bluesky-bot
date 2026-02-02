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
from webdriver_manager.chrome import ChromeDriverManager
from atproto import Client, client_utils

# CONFIG
BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE")
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD")
PROMO_URL = "https://shop.canaries.co.uk/page/discountsandpromotions"
SEEN_FILE = "seen_promos.json"

# Keywords to trigger a post
KEYWORDS = ["FREE", "% OFF", "SALE", "OFFER", "DISCOUNT", "PRICE DROP", "CLEARANCE"]

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f: 
                return set(json.load(f))
        except Exception as e: 
            print(f"⚠️ Warning: Could not parse {SEEN_FILE}: {e}")
            return set()
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f: 
        json.dump(list(seen), f, indent=2)
    print(f"💾 Saved {len(seen)} total promos to local history.")

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Added to prevent detection and window issues
    options.add_argument("--window-size=1920,1080") 
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def scrape_promos(driver):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛍️ Checking shop promotions...")
    driver.get(PROMO_URL)
    promos = []
    
    try:
        wait = WebDriverWait(driver, 20)
        # Ensure the main content is loaded
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".cms-content")))
        
        # Select headers and paragraphs
        content_sections = driver.find_elements(By.CSS_SELECTOR, ".cms-content h2, .cms-content h3, .cms-content p")
        
        for section in content_sections:
            text = section.text.strip()
            
            # Filter logic: Must contain keyword AND be long enough to be a sentence
            if any(kw in text.upper() for kw in KEYWORDS):
                if 10 < len(text) < 300: # Ignore tiny fragments or massive blocks
                    # Exclude common footer/cookie noise
                    if "cookie" not in text.lower() and "privacy policy" not in text.lower():
                        promos.append({"headline": text, "url": PROMO_URL})
        
        print(f"✅ Scraper found {len(promos)} potential matches.")
        return promos

    except Exception as e:
        print(f"❌ Shop Scraper Error: {e}")
        # Raising the error allows GitHub Action to trigger a Retry
        raise e

def post_to_bluesky(promo, client):
    print(f"📤 Posting to Bluesky: {promo['headline'][:50]}...")
    
    tb = client_utils.TextBuilder()
    tb.text(f"🛍️ SHOP DEAL: {promo['headline']} \n\n")
    tb.link("Click here to view deals", promo['url'])
    tb.text("\n\n_____\nNorwich City Shop 🔰 ")
    tb.tag("#NCFC", "NCFC")
    tb.tag("#Canaries", "Canaries")

    try:
        client.send_post(text=tb)
        return True
    except Exception as e:
        print(f"❌ Bluesky Post Failed: {e}")
        return False

def main():
    seen = load_seen()
    driver = None
    
    try:
        driver = setup_driver()
        found_promos = scrape_promos(driver)
    finally:
        if driver:
            driver.quit()

    # Filter for brand new promos
    new_promos = [p for p in found_promos if p["headline"] not in seen]
    
    if not new_promos:
        print("⏭️ No new promotions to post today.")
        return

    # Login and Post
    try:
        client = Client()
        client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)
        
        # Post the top one found
        latest = new_promos[0]
        if post_to_bluesky(latest, client):
            seen.add(latest["headline"])
            save_seen(seen)
        else:
            print("⚠️ Skipping history update because post failed.")
            
    except Exception as e:
        print(f"❌ Critical error in Main: {e}")
        raise e

if __name__ == "__main__":
    main()
    
