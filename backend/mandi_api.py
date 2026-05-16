import requests

API_KEY = "579b464db66ec23bdd0000018c1f02d45f2346545898793b192baab3"

RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"

BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"


def fetch_prices(
    commodity,
    state=None,
    district=None,
    limit=20
):

    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": limit,
        "filters[Commodity]": commodity
    }

    if state:
        params["filters[State]"] = state

    if district:
        params["filters[District]"] = district

    print("Fetching from API...")

    try:

        response = requests.get(
            BASE_URL,
            params=params,
            timeout=3
        )

        data = response.json()

        prices = []

        for record in data.get("records", []):

            try:
                prices.append(
                    float(record["Modal_Price"])
                )

            except:
                continue

        print("Fetched Prices:", prices)

        return prices

    except Exception as e:

        print("Government API failed:", e)

        # instantly return empty list
        return []