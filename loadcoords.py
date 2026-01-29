import requests
import pandas as pd
import time
import ee
import geemap.core as geemap
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
ee.Authenticate()
ee.Initialize(project='PROJECT_ID')
BRANDS = [
    "WMT",
    "TGT",
    "COST",
    "HD",
    "LOW",
    "BBY"
]
def overpass_query(brand):
    return f"""
    [out:json][timeout:120];
    area["ISO3166-1"="US"]->.usa;
    (
      node["brand"="{brand}"](area.usa);
      way["brand"="{brand}"](area.usa);
      relation["brand"="{brand}"](area.usa);
    );
    out center tags;
    """

def fetch_brand_locations(brand):
    response = requests.post(
        OVERPASS_URL,
        data={"data": overpass_query(brand)}
    )
    response.raise_for_status()
    data = response.json()["elements"]

    records = []
    for el in data:
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")

        if lat and lon:
            records.append({
                "brand": brand,
                "lat": lat,
                "lon": lon,
                "name": el.get("tags", {}).get("name")
            })

    return records

all_records = []

for brand in BRANDS:
    print(f"Fetching {brand} locations...")
    all_records.extend(fetch_brand_locations(brand))
    time.sleep(5)  

df = pd.DataFrame(all_records)
df.drop_duplicates(subset=["brand", "lat", "lon"], inplace=True)

df.to_csv("retail_store_coordinates.csv", index=False)
print("Saved to retail_store_coordinates.csv")

