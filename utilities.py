###############################################################################
#                         HELPER FUNCTIONS                                    #
###############################################################################
import requests
import re
import logging
import json
import os
from datetime import datetime


def load_config(CONFIG_FILE):
    """
    Loads the Studélites and ARPEJ URLs from the external JSON config file.
    Returns (studelites_urls, arpej_urls) as lists.
    """
    if not os.path.exists(CONFIG_FILE):
        logging.error(f"Config file {CONFIG_FILE} not found!")
        return [], []
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            studelites_urls = data.get("studelites_urls", [])
            arpej_urls = data.get("arpej_urls", [])
            return studelites_urls, arpej_urls
    except Exception as e:
        logging.error(f"Error reading {CONFIG_FILE}: {e}")
        return [], []

def load_seen_ids(SEEN_IDS_FILE):
    """
Loads the dictionary of seen listings. Example structure:
    {
    "STUDELITES:N°0139/221": { "first_seen": "2025-02-18T14:32:56" },
    "ARPEJ2:https://...":     { "first_seen": "2025-02-18T16:05:12" }
    }
"""
    if os.path.exists(SEEN_IDS_FILE):
        try:
            with open(SEEN_IDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data  # a dict of { unique_id: { "first_seen": "..." } }
        except Exception as e:
            logging.error("Could not read %s: %s", SEEN_IDS_FILE, e)
    return {}

def save_seen_ids(seen_dict, SEEN_IDS_FILE):
    """
    Saves the dictionary of seen listings, with ISO8601 timestamps under "first_seen".
    """
    try:
        with open(SEEN_IDS_FILE, "w", encoding="utf-8") as f:
            json.dump(seen_dict, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error("Could not write %s: %s", SEEN_IDS_FILE, e)


def send_telegram_message(TOKEN, TELEGRAM_CHAT_ID, message: str) -> None:
    """
    Sends a Telegram message with the given text (plain text).
    If you want HTML formatting, add 'parse_mode': 'HTML' in the payload.
    """
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logging.info("Message sent successfully")
        else:
            logging.error("Failed to send message: %s", response.text)
    except Exception as e:
        logging.error("Error sending message: %s", str(e))

def parse_surface(surface_str):
    """
    Extract a float from a string like '40.81m²' or '17,8'.
    Returns None if parsing fails.
    """
    if not surface_str:
        return None
    
    match = re.search(r'([\d.,]+)', surface_str)
    if match:
        val_str = match.group(1).replace(",", ".")  # e.g. "40,81" -> "40.81"
        try:
            return float(val_str)
        except ValueError:
            return None
    return None

def parse_price(price_str):
    """
    Extract a float from a string like '1 483,74 €' or '549.05€'.
    Returns None if parsing fails.
    """
    if not price_str:
        return None
    
    # Remove spaces, '€', etc.
    cleaned = price_str.replace(" ", "")  # e.g. "1483,74€"
    match = re.search(r'([\d.,]+)', cleaned)
    if match:
        val_str = match.group(1).replace(",", ".")
        try:
            return float(val_str)
        except ValueError:
            return None
    return None