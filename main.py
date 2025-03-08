#!/Users/asaucedo/Programming/wunderflats-scrape/.venv/bin/python
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import subprocess
import datetime

BASE_URL = "https://wunderflats.com"
PATH_URL = "/en/furnished-apartments/berlin"
QUERY_URL = "?from=2025-05-06&to=2026-04-03&scoreVariant=A&bbox=13.439029194122513%2C52.51287794429001%2C13.500998951202591%2C52.48638676462957&minSize=80"
SAVE_FILE = "flats-cache.json"

class WunderManager:
    def __init__(self, save_file=SAVE_FILE):
        self._sync = False
        self._save_file = save_file

    def load(self):
        self._old = self._fetch_old()
        self._new = self._fetch_new()
        self._sync = True

    def _fetch_old(self):
        try:
            with open(self._save_file, "r") as f:
                listings = json.load(f)
        except FileNotFoundError:
            return {}
        return listings

    def _fetch_new(self) -> dict:
        listings = {}

        i = 0
        while True:
            i += 1
            url = f"{BASE_URL}{PATH_URL}/{i}{QUERY_URL}"
            r = requests.get(url)
            if not r.status_code:
                raise Exception("Error")
            soup = BeautifulSoup(r.text, "html.parser")
            web_listings = soup.select("div.ListingsList-item")

            if len(web_listings) < 1:
                break

            for web_listing in web_listings:
                uid = web_listing.find("a").get("data-listing")
                title = web_listing.find("h3").text
                price = web_listing.find("span", class_="ListingPrice-price").text
                calendar = web_listing.find("small", class_="ListingPrice-time").text
                img = web_listing.find("img").get("src")
                rooms, people, size = [l.text for l in web_listing.find_all("span", class_="info")]
                url = web_listing.find("a").get("href")

                listings[uid] = {
                    "id": uid,
                    "title": title,
                    "price": int(price.replace("€", "").replace(",", "")),
                    "calendar": calendar.split()[1],
                    "rooms": int(rooms.split()[0]),
                    "people": int(people.split()[0]),
                    "img": img,
                    "url": url,
                    "size": int(size.split()[0])
                }

        return listings

    def process(self) -> str:
        if not self._sync:
            self.load()

        self._new_listings = {k:v for k,v in self._new.items() if k not in self._old}
        self._removed_listings = {k:v for k,v in self._old.items() if k not in self._new}

        return self._construct_body(self._new_listings, self._removed_listings)


    @staticmethod
    def send_mail(content, subject):
        """use applescript to create a mail message"""
        properties = ["visible:true"]
        properties.append(f'subject:"{subject}"')
        properties.append('sender:"alejandro.zalando@icloud.com"')
        properties.append(f'content:"{content}"')
        properties_string = ",".join(properties)
        make_new = []
        make_new.extend(['make new to recipient with properties {address:"alejandro.saucedo@zalando.de"}'])
        make_new.append('send')
        make_new_string = "tell result\n" + "\n".join(make_new) + \
            "\nend tell\n"
        script = """tell application "mail"
        make new outgoing message with properties {%s}
        %s end tell
        """ % (properties_string, make_new_string)
        # run applescript
        return subprocess.getoutput(f'/usr/bin/osascript << eof\n{script}\neof')


    def _construct_body(self, l_added, l_rm):
        body = "\n"
        body += "NEW PROPERTIES:\n\n"
        body += "\n".join([self._construct_body_listing(v) for k,v in l_added.items()])
        body += "\n\n\n"
        body += "REMOVED PROPERTIES:\n\n"
        body += "\n".join([self._construct_body_listing(v) for k,v in l_rm.items()])
        body += "\n\n\n\n\n\n"
        body += "-- ALL PROPERTIES --\n\n"
        body += "\n".join([self._construct_body_listing(v) for k,v in self._new.items()])
        return body

    def _construct_body_listing(self, listing: dict):
        body = f"{listing["title"]}\n"
        body += f"Rooms: {listing["rooms"]}\t"
        body += f"Price: €{listing["price"]}.00\t"
        body += f"Size: {listing["size"]} m²\t/n"
        body += f"{BASE_URL}{listing["url"]}\n"
        return body

    def save_new(self):
        if not self._sync:
            self.load()

        with open(self._save_file, "w") as f:
            json.dump(self._new, f)



if __name__ == "__main__":
    print(f"Script started {datetime.datetime.now()}")
    try:
        wm = WunderManager()
        message = wm.process()
        wm.save_new()

        subject = "NEW PROPERTIES" if wm._new_listings else "NONE"
        WunderManager.send_mail(message, f"WunderFlats: {subject}")

    except Exception as e:
        # Print for apple logs and send email
        print(e)
        WunderManager.send_mail(f"Error: {e}", "WunderManager Script Error")

