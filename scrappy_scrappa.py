import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import quote
import utilities
from datetime import datetime,timedelta



###############################################################################
#                    SCRAPING STUDELITES RESIDENCES                           #
###############################################################################

def scrape_studelites(TOKEN, TELEGRAM_CHAT_ID, studelites_urls, seen_ids):
    """
    Scrapes the given Studélites URLs, applies filtering (price vs surface),
    and sends Telegram messages for any *new* matching apartments.
    Returns the updated `seen_ids`.
    """
    for url in studelites_urls:
        logging.info(f"[Studélites] Scraping {url}")
        try:
            response = requests.get(url, timeout=15)
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            logging.error(f"Failed to fetch {url}: {e}")
            continue

        # Page-level address (if any) is in <div class="bloc">
        address_div = soup.find("div", class_="bloc")
        address_text = None
        if address_div:
            address_text = " ".join(address_div.stripped_strings)

        # Find apartments: <div class="appart-item element-item">
        appart_items = soup.find_all("div", class_="appart-item element-item")

        for item in appart_items:
            # Skip items with <small>Plus de logements disponibles...
            small_tag = item.find("small")
            if small_tag and "Plus de logements disponibles" in small_tag.get_text():
                continue

            # Extract lot ID: <div class="lot">N°0139/221</div>
            lot_div = item.find("div", class_="lot")
            lot_id = lot_div.get_text(strip=True) if lot_div else None
            if not lot_id:
                continue

            # Build a unique key for this listing
            unique_key = f"STUDELITES:{lot_id}"

            # -- If we've never seen it, treat as new:
            if unique_key not in seen_ids:
                notify = True  # definitely new
            else:
                # We've seen this ID before: check the timestamp
                first_seen_str = seen_ids[unique_key].get("first_seen")
                if not first_seen_str:
                    # If for some reason there's no timestamp, treat as new
                    notify = True
                else:
                    # Convert ISO string to datetime
                    first_seen_dt = datetime.fromisoformat(first_seen_str)
                    # 7 days old threshold
                    seven_days_ago = datetime.now() - timedelta(days=7)
                    
                    if first_seen_dt < seven_days_ago:
                        # older than 7 days => re-notify
                        notify = True
                    else:
                        # it's more recent than 7 days => skip
                        notify = False
        
            if notify:

                # Extract Type
                type_div = item.find("div", class_="type")
                type_text = type_div.get_text(strip=True) if type_div else None
                if type_text:
                    # remove the literal "Type"
                    type_text = type_text.replace("Type", "").strip()

                # Extract Price
                price_div = item.find("div", class_="price")
                raw_price_text = price_div.get_text(strip=True) if price_div else None
                if raw_price_text:
                    # remove "TTC" if present
                    raw_price_text = raw_price_text.replace("TTC", "").strip()
                parsed_price = utilities.parse_price(raw_price_text)

                # Extract Surface & Disponibilité from <li> elements
                surface_text = None
                availability_text = None
                for li in item.find_all("li"):
                    li_text = li.get_text(strip=True)
                    if "Surface" in li_text:
                        surface_text = li_text.replace("Surface :", "").strip()
                    if "Disponibilité" in li_text:
                        availability_text = li_text.replace("Disponibilité :", "").strip()

                parsed_surface = utilities.parse_surface(surface_text)

                # -- Filter logic: 
                #   If surface < 25 => price < 800
                #   Else (>=25) => price < 1200
                if parsed_surface is None or parsed_price is None:
                    continue

                if parsed_surface < 25:
                    if parsed_price >= 800:
                        continue
                else:  # surface >= 25
                    if parsed_price >= 1200:
                        continue

                # --- Construct the message ---
                message_parts = []
                message_parts.append(f"Résidence: {url}")  # Which Studélites page
                # If there's an address, we build a Google Maps link
                if address_text:
                    gmaps_link = f"https://www.google.com/maps/search/{quote(address_text)}"
                    message_parts.append(f"Adresse: {gmaps_link}")
                if type_text:
                    message_parts.append(f"Type: {type_text}")
                if surface_text:
                    message_parts.append(f"Surface: {surface_text}")
                if raw_price_text:
                    message_parts.append(f"Loyer: {raw_price_text}")
                if availability_text:
                    message_parts.append(f"Disponibilité: {availability_text}")

                final_message = "\n".join(message_parts)
                if not final_message.strip():
                    final_message = "Logement disponible (aucune information supplémentaire)"

                # Send Telegram message
                utilities.send_telegram_message(TOKEN, TELEGRAM_CHAT_ID, final_message)

            # Mark this lot as seen
            seen_ids[unique_key] = {
                "first_seen": datetime.now().isoformat(timespec='seconds')
            }

        logging.info(f"[Studélites] Finished processing {url}")

    return seen_ids


###############################################################################
#                    SCRAPING ARPEJ RESIDENCE DETAILS                         #
###############################################################################

def scrape_arpej_detail_pages(TOKEN, TELEGRAM_CHAT_ID, arpej_urls, seen_ids):
    """
    Scrapes a list of ARPEJ residence detail pages with the structure described.
    Extracts:
      - Type/Name (from <h1 class="description-title">)
      - Google Maps link (from <a class="description-destination">)
      - Price, surface, nb logements, disponibilité, “Je dépose mon dossier”
    Returns the updated seen_ids.
    """
    for page_url in arpej_urls:
        logging.info(f"[ARPEJ] Scraping {page_url}")

        unique_key = f"ARPEJ2:{page_url}"
        # -- If we've never seen it, treat as new:
        if unique_key not in seen_ids:
            notify = True  # definitely new
        else:
            # We've seen this ID before: check the timestamp
            first_seen_str = seen_ids[unique_key].get("first_seen")
            if not first_seen_str:
                # If for some reason there's no timestamp, treat as new
                notify = True
            else:
                # Convert ISO string to datetime
                first_seen_dt = datetime.fromisoformat(first_seen_str)
                # 7 days old threshold
                seven_days_ago = datetime.now() - timedelta(days=7)
                
                if first_seen_dt < seven_days_ago:
                    # older than 7 days => re-notify
                    notify = True
                else:
                    # it's more recent than 7 days => skip
                    notify = False
    
        if not notify:
            logging.info(f"Already seen this ARPEJ page: {page_url}, skipping.")
            seen_ids[unique_key] = {"first_seen": datetime.now().isoformat(timespec='seconds')}

            continue

        try:
            resp = requests.get(page_url, timeout=15)
        except Exception as e:
            logging.error(f"Failed to fetch {page_url}: {e}")
            continue
        
        if resp.status_code != 200:
            logging.error(f"Non-200 status code for {page_url}: {resp.status_code}")
            continue
        
        soup = BeautifulSoup(resp.text, "html.parser")

        # 1) Type + Name
        h1_tag = soup.find("h1", class_="description-title")
        if h1_tag:
            type_name_text = h1_tag.get_text(" ", strip=True)
        else:
            type_name_text = "Type / Name inconnus"

        # 2) Google Maps link
        maps_link = None
        maps_anchor = soup.find("a", class_="description-destination")
        if maps_anchor and maps_anchor.get("href"):
            maps_link = maps_anchor["href"]

        # 3) Price, surface, disponibilité, “Je dépose mon dossier”
        bloc_ibail = soup.find("div", class_="bloc-ibail")
        price_text = None
        surface_text = None
        disponibilite = None
        dossier_link = None

        if bloc_ibail:
            # Price: <div class="folder-price">…</div>
            folder_price_div = bloc_ibail.find("div", class_="folder-price")
            if folder_price_div:
                price_text = folder_price_div.get_text(" ", strip=True)

            # <ul class="folder-points"> -> each <li> has label + figure
            ul_points = bloc_ibail.find("ul", class_="folder-points")
            if ul_points:
                lis = ul_points.find_all("li")
                for li in lis:
                    label = li.find("span", class_="folder-points__text")
                    figure = li.find("span", class_="folder-points__figure")
                    if not label or not figure:
                        continue
                    label_text = label.get_text(strip=True).lower()
                    figure_text = figure.get_text(strip=True)

                    if "surface" in label_text:
                        surface_text = figure_text
                    elif "disponibilité" in label_text:
                        disponibilite = figure_text

            # “Je dépose mon dossier” link
            a_dossier = bloc_ibail.find("a", class_="folder-cta")
            if a_dossier and a_dossier.get("href"):
                dossier_link = a_dossier["href"]

        # 4) Build the message
        message_parts = []
        message_parts.append(f"Résidence: {page_url}")
        message_parts.append(f"Type & Name: {type_name_text}")

        if maps_link:
            message_parts.append(f"Google Maps: {maps_link}")
        if price_text:
            message_parts.append(f"Prix: {price_text}")
        if surface_text:
            message_parts.append(f"Surface: {surface_text}")
        if disponibilite:
            message_parts.append(f"Disponibilité: {disponibilite}")
        if dossier_link:
            message_parts.append(f"Je dépose mon dossier: {dossier_link}")

        final_message = "\n".join(message_parts)
        if not final_message.strip():
            final_message = "Aucune information trouvée sur cette résidence."

        # 5) Send Telegram
        utilities.send_telegram_message(TOKEN, TELEGRAM_CHAT_ID, final_message)

        # Mark as seen
        logging.info(f"[ARPEJ] Marking as seen: {unique_key}")
        seen_ids[unique_key] = {"first_seen": datetime.now().isoformat(timespec='seconds')}

    return seen_ids


