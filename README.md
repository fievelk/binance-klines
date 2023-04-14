# README

## Binance Downloader

Binance Downloader is a CLI tool and Python library used to download historical OHLCV klines from Binance. It works asynchronously to download data from multiple symbols concurrently.


### Prerequisites

- Python >= 3.11
- Binance API Keys


### Installation

- Clone the project
- `pip install .`


### Usage

The tool can be used as a command line tool or as a python module.

#### From command line

```sh
# To check the available CLI options
binance_downloader --help
# To download data
binance_downloader --start-date "2022-07-18 00:00:00" \
    --end-date "2022-07-20 23:59:00" --timeframe '1m' --output-dir .data/ \
    --symbols BTC/USDT ETH/USDT
```

#### As a Python module

```py
import asyncio
import datetime

from binance_downloader import BinanceOHLCVDownloader

async def main():
    downloader = BinanceOHLCVDownloader()
    start_date = datetime.datetime(2020, 9, 1).replace(tzinfo=pytz.utc)
    end_date = datetime.datetime(2020, 9, 2).replace(tzinfo=pytz.utc)

    try:
        # Download data for a single symbol. Data is downloaded in batches.
        async for batch in downloader.fetch_ohlcv(
            symbol="BTC/USDT",
            start_date=start_date,
            end_date=end_date,
            timeframe="30m",
        ):
            print(batch)
    finally:
        await downloader.exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
```
