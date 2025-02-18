import logging
import schedule
import utilities
import scrappy_scrappa


# Set up basic logging (optional)
logging.basicConfig(level=logging.INFO)

# Your Telegram credentials (replace with real values)
TOKEN = "7702053498:AAFk1PF5cUOTQtPLuRCBtyBvhAsGv2drbzY"
TELEGRAM_CHAT_ID = "6944770884"

# File to store "seen" IDs (covers both Studélites and Arpej)
SEEN_IDS_FILE = "seen_ids.json"

# File where we read our config of URLs
CONFIG_FILE = "scraping_config.json"



###############################################################################
#                         MASTER SCRAPING FUNCTION                            #
###############################################################################

def main():
    """
    Loads the URL config, loads seen IDs, scrapes both Studélites & ARPEJ, 
    updates the JSON file. Runs once per invocation (every 2 hours).
    """
    # Load config from JSON
    studelites_urls, arpej_urls = utilities.load_config(CONFIG_FILE)

    # If empty, we won't do anything
    if not studelites_urls and not arpej_urls:
        logging.warning("No URLs found in config file!")
        return

    # Load previously seen IDs
    seen_ids = utilities.load_seen_ids(SEEN_IDS_FILE)

    # 1) Scrape Studélites
    if studelites_urls:
        seen_ids = scrappy_scrappa.scrape_studelites(TOKEN, TELEGRAM_CHAT_ID, studelites_urls, seen_ids)

    # 2) Scrape ARPEJ detail pages
    if arpej_urls:
        seen_ids = scrappy_scrappa.scrape_arpej_detail_pages(TOKEN, TELEGRAM_CHAT_ID, arpej_urls, seen_ids)

    # Save updated IDs
    utilities.save_seen_ids(seen_ids,SEEN_IDS_FILE)

    

if __name__ == "__main__":
    main()
