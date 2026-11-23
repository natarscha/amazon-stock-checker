
import json
import os
import time
import requests
from bs4 import BeautifulSoup

ENDPOINT = os.environ["CLOUDFLARE_ENDPOINT"]
TOKEN = os.environ["STOCK_SYNC_TOKEN"]

def check_stock(asin):
    url = f"https://www.amazon.com.au/dp/{asin}"

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "en-AU,en;q=0.9"
            },
            timeout=25
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Amazon may expose availability in JSON-LD.
        for script in soup.select(
            'script[type="application/ld+json"]'
        ):
            try:
                data = json.loads(script.string or "{}")
            except (ValueError, TypeError):
                continue

            def find_availability(obj):
                if isinstance(obj, list):
                    for item in obj:
                        result = find_availability(item)
                        if result:
                            return result
                elif isinstance(obj, dict):
                    availability = obj.get("availability")
                    if isinstance(availability, str):
                        return availability
                    for value in obj.values():
                        result = find_availability(value)
                        if result:
                            return result
                return None

            availability = find_availability(data)

            if availability:
                if availability.endswith("/InStock"):
                    return "in_stock"
                if availability.endswith("/OutOfStock"):
                    return "out_of_stock"

        return "unknown"

    except requests.RequestException as error:
        print(f"Failed to check {asin}: {error}")
        return "unknown"


with open("products.json", encoding="utf-8") as file:
    products = json.load(file)

for product in products:
    asin = product["asin"].upper()
    status = check_stock(asin)

    print(f"{asin}: {status}")

    payload = {
        "asin": asin,
        "status": status,
        "availability_text": ""
    }

    response = requests.post(
        ENDPOINT,
        json=payload,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=20
    )

    response.raise_for_status()
    time.sleep(5)

