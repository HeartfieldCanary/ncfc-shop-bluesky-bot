import os
import json
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from atproto import Client, models, client_utils

# CONFIG
BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE")
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD")
PROMO_URL = "https://shop.canaries.co.uk/page/discountsandpromotions"
SEEN_FILE = "seen_promos.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f: return set(json.load(f))
        except: return set()
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f: json.dump(list(seen), f, indent=2)

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def scrape_promos(driver):
    print(f"🛍️ Checking shop promotions...")
    driver.get(PROMO_URL)
    promos = []
    try:
        wait = WebDriverWait(driver, 20)
        # Wait for the main content area of the shop page
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".cms-content")))
        
        # The shop uses standard paragraph/heading tags for promos
        content_sections = driver.find_elements(By.CSS_SELECTOR, ".cms-content h3, .cms-content p")
        
        for section in content_sections:
            text = section.text.strip()
            # Filter for meaningful promo text (e.g., "Free Printing", "% off", "Sale")
            if any(kw in text.upper() for kw in ["FREE", "% OFF", "SALE", "OFFER", "DISCOUNT"]):
                if len(text) > 10: # Avoid tiny fragments
                    promos.append({"headline": text, "url": PROMO_URL})
    except Exception as e:
        print(f"⚠️ Shop Scraper Error: {e}")
    return promos

def post_to_bluesky(promo, client):
    print(f"📤 Posting Promo: {promo['headline'][:50]}...")
    
    text_builder = client_utils.TextBuilder()
    text_builder.text(f"🛍️ SHOP DEAL: {promo['headline']} | ")
    text_builder.link("View Deals", promo['url'])
    text_builder.text("\n\n_____\nNorwich City Shop 🔰 ")
    text_builder.tag("#NCFC", "NCFC")

    try:
        client.send_post(text=text_builder)
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def main():
    seen = load_seen()
    driver = setup_driver()
    found_promos = scrape_promos(driver)
    driver.quit()

    # Filter for brand new text we haven't posted
    new_promos = [p for p in found_promos if p["headline"] not in seen]
    
    if not new_promos:
        print("✅ No new promotions found.")
        return

    client = Client()
    client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)
    
    # Just post the most recent/top one to avoid spamming
    latest = new_promos[0]
    if post_to_bluesky(latest, client):
        seen.add(latest["headline"])
        save_seen(seen)

if __name__ == "__main__":
    main()
