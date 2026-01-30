import pandas as pd
import numpy as np
import yfinance as yf
from matplotlib import pyplot as plt
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
config.sh_client_secret = "..."

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
trading_days = returns.index


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
def next_trading_day(date, trading_days):
    return trading_days[trading_days >= date][0]

df["signal"] = (
    df.groupby("date")["feature"]
      .rank(pct=True) - 0.5
)
df["signal"] /= (
    df.groupby("date")["signal"]
      .transform(lambda x: x.abs().sum())
)
df["trade_date"] = df["date"].apply(
    lambda d: next_trading_day(d, trading_days)
)
df["ret"] = df.apply(
    lambda x: returns.loc[x["trade_date"], x["ticker"]],
    axis=1
)
df["pnl"] = df["signal"] * df["ret"]
daily_pnl = df.groupby("date")["pnl"].sum()
sharpe = np.sqrt(252) * daily_pnl.mean() / daily_pnl.std()
cum_pnl = (1 + daily_pnl).cumprod()
ic = (
    df.groupby("date")[["signal", "ret"]]
      .corr()
      .iloc[0::2, -1]
      .mean()
)
print(sharpe)
print(daily_pnl)
print(cum_pnl)
print(ic)
df.to_csv("trade_results.csv",index=False)



equity = (1 + daily_pnl).cumprod()

plt.figure(figsize=(10,4))
plt.plot(equity)
plt.title("Equity Curve")
plt.ylabel("Portfolio Value")
plt.xlabel("Date")
plt.show()

rolling_max = equity.cummax()
drawdown = equity / rolling_max - 1

plt.figure(figsize=(10,4))
plt.plot(drawdown)
plt.title("Drawdown")
plt.ylabel("Drawdown")
plt.xlabel("Date")
plt.show()

df["signal_lag"] = df.groupby("ticker")["signal"].shift(1)
df["turnover"] = (df["signal"] - df["signal_lag"]).abs()

daily_turnover = df.groupby("date")["turnover"].sum()
TCOST = 0.0005

daily_cost = TCOST * daily_turnover
daily_pnl_net = daily_pnl - daily_cost
equity_net = (1 + daily_pnl_net).cumprod()

sharpe_net = np.sqrt(252) * daily_pnl_net.mean() / daily_pnl_net.std()
plt.figure(figsize=(10,4))
plt.plot(equity, label="Gross")
plt.plot(equity_net, label="Net")
plt.legend()
plt.title("Equity Curve (Gross vs Net)")
plt.show()

sharpe_net = np.sqrt(252) * daily_pnl_net.mean() / daily_pnl_net.std()
stats = {
    "Sharpe (gross)": np.sqrt(252) * daily_pnl.mean() / daily_pnl.std(),
    "Sharpe (net)": sharpe_net,
    "Max drawdown": drawdown.min(),
    "Avg daily turnover": daily_turnover.mean()
}
print(stats)
pd.Series(stats)