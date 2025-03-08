#!/Users/asaucedo/.pyenv/shims/python
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import subprocess
import datetime

BASE_URL = "https://wunderflats.com/en/furnished-apartments/berlin"
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
            url = f"{BASE_URL}/{i}{QUERY_URL}"
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

        pd_new = pd.DataFrame(self._new.values())
        pd_old = pd.DataFrame(self._old.values())
        if not self._old:
            pd_added = pd_new
            pd_removed = pd.DataFrame(None, None, pd_new.columns)
        else:
            pd_added = pd_new[~pd_new.id.isin(pd_old.id)]
            pd_removed = pd_old[~pd_old.id.isin(pd_new.id)]

        return self._construct_body(pd_added, pd_removed, pd_new)

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


    def _construct_body(self, pd_added, pd_removed, pd_all):
        body = "\n"
        body += "NEW PROPERTIES:\n\n"
        body += pd_added[["title", "price", "rooms", "size", "id"]].to_markdown()
        body += "\n\n\n"
        body += "REMOVED PROPERTIES:\n\n"
        body += pd_removed[["title", "price", "rooms", "size", "id"]].to_markdown()
        body += "\n\n\n\n\n\n"
        body += "-- ALL PROPERTIES --\n\n"
        body += pd_all.to_markdown()
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
        WunderManager.send_mail(message, "New WunderFlats")

    except Exception as e:
        # Print for apple logs and send email
        print(e)
        WunderManager.send_mail(f"Error: {e}", "WunderManager Script Error")
    else:
        WunderManager.send_mail("All good", "WunderManager All Good")

