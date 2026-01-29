import pandas as pd
import numpy as np
import yfinance as yf

from sentinelhub import (
    SHConfig,
    SentinelHubRequest,
    DataCollection,
    BBox,
    CRS,
    bbox_to_dimensions
)

stores=pd.read_csv("retail_store_coordinates.csv")
config = SHConfig()
config.sh_client_id = "1bea8abb-783a-4ed5-abab-8dc486810d82"
config.sh_client_secret = "wuB0b9jxy4RTI1oNVJ2Ak1AXvNihigOH"

def make_bbox(lat, lon, meters=200):
    d = meters / 111_000  # approx deg per meter
    return BBox(
        bbox=[lon - d, lat - d, lon + d, lat + d],
        crs=CRS.WGS84
    )

store_bboxes = {
    row.brand: make_bbox(row.lat, row.lon)
    for _, row in stores.iterrows()
}
VALSCRIPT = """
//VERSION=3
function setup() {
    return {
        input: ["B02", "B03", "B04"],
        output: { bands: 3 }
    };
}
function evaluatePixel(sample) {
    return [sample.B04, sample.B03, sample.B02];
}
"""

def get_satellite_patch(bbox, start_date, end_date, size=(20,20)):
    request = SentinelHubRequest(
        evalscript=VALSCRIPT,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A,
                time_interval=(start_date, end_date),
                mosaicking_order="leastCC"
            )
        ],
        responses=[
            SentinelHubRequest.output_response("default", "tiff")
        ],
        bbox=bbox,
        size=size,
        config=config   # uses your SHConfig
    )
    return request.get_data()[0]
dates = pd.date_range("2023-01-01", "2023-03-01", freq="7D")

records = []
def parking_lot_feature(img):
    """
    img: NumPy array (H, W, 3) from Sentinel-2
    returns: scalar feature
    """
    gray = img.mean(axis=2)
    return np.std(gray) / (np.mean(gray) + 1e-6)

for brand, bbox in store_bboxes.items():
    for d in dates:
        img = get_satellite_patch(
            bbox,
            d.strftime("%Y-%m-%d"),
            (d + pd.Timedelta(days=3)).strftime("%Y-%m-%d")
        )
        feat = parking_lot_feature(img)
        records.append({
            "date": d,
            "ticker": brand,
            "feature": feat
        })

df = pd.DataFrame(records)
#print(df)
df.to_csv("feature_data.csv", index=False)

tickers = list(store_bboxes.keys())
#print(tickers)
prices = (
    yf.download(
        tickers,
        start="2022-01-01",
        end="2024-01-01",
        auto_adjust=True,
        progress=False
    )["Close"]
)
#print(prices)

returns = prices.pct_change().shift(-1)
#print(returns)

earnings = {}

for t in tickers:
    cal = yf.Ticker(t).earnings_dates
    earnings[t] = cal.index.tz_localize(None).normalize()
#print(earnings)

def in_earnings_window(date, earnings_dates, pre=5, post=1):
    for e in earnings_dates:
        if e - pd.Timedelta(days=pre) <= date <= e + pd.Timedelta(days=post):
            return True
    return False
df["trade"] = df.apply(
    lambda x: in_earnings_window(
        x["date"], earnings[x["ticker"]]
    ),
    axis=1
)
df = df[df["trade"]]
df.to_csv("trade_results.csv",index=False)
