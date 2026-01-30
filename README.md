**Overview**
This project explores how satellite images of retail store parking lots can be used as a source of alternative data for quantitative trading. The goal is to understand how real-world activity, such as how full a parking lot is, can be turned into a numerical feature and then connected to stock returns.

Rather than building a large-scale data pipeline, this project focuses on demonstrating the idea clearly: from image → feature → trading signal.

**Why This Project**
Most trading strategies rely on price data or financial statements. I was interested in whether physical activity captured in satellite images could provide a different perspective on consumer demand.

Retail parking lots are a useful proxy because higher foot traffic may reflect stronger sales, especially around earnings periods. This project looks at how that information could be incorporated into a systematic trading framework.

**Data**
Satellite Images

-A small set of satellite images of retail parking lots (such as Walmart and Target)

Images are used as example alternative data and are linked to a store ticker and date

The limited dataset is intentional and keeps the project focused on methodology

Market Data

-Daily stock price data for the same companies

-Earnings dates to align signals with earnings-related trading logic

**Feature Construction**

Each satellite image is converted into a single numerical feature that serves as a proxy for parking lot occupancy. The feature is based on simple image properties such as brightness or edge density.
**Signal and Strategy**
-Features are organized by date and ticker

-Signals are ranked cross-sectionally to create long and short positions

-Signals are lagged to avoid lookahead bias

-Portfolio weights are normalized to control overall exposure

-The strategy is designed to be systematic and market-neutral, with trades aligned around earnings windows.

**Backtesting**
The backtest evaluates:

-Daily portfolio returns

-Cumulative performance over time

-Drawdowns from peak equity

-The impact of transaction costs

-The results are meant to be illustrative and focus on whether the pipeline and logic are sound rather than on maximizing performance.
