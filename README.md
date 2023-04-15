# BinanceKlines downloader

BinanceKlines downloader is a simple command line tool and Python library used to download OHLCV k-lines from Binance. It works asynchronously to download candlestick market data from multiple symbols concurrently.


## Installation

```console
$ git clone git@github.com:fievelk/binance-klines.git  # Clone the project
$ cd binance-klines/
$ pip install .
```

## Usage

BinanceKlines can be used both as command line tool and python module. The package fetches data from Binance's [`GET /api/v3/klines`](https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data) endpoint. Since this endpoint is [flagged as `SECURITY_TYPE = NONE`](https://binance-docs.github.io/apidocs/spot/en/#endpoint-security-type) in Binance docs, it is not necessary to provide an API key to download the data.


### From command line

You can check all the available options using `binance-klines --help`.

```console
$ binance-klines --help
usage: binance-klines [-h] [-v] --start-date START_DATE [--end-date END_DATE] [--output-dir OUTPUT_DIR] [--timeframe {1m,3m,5m,15m,30m,1h,2h,4h,6h,8h,12h,1d,3d,1w,1M}] symbols [symbols ...]

positional arguments:
  symbols               The list of currencies whose OHLCV will be fetched.

options:
  -h, --help            show this help message and exit
  -v, --verbose         Increase output verbosity. -v: INFO, -vv: DEBUG.
                        Default: WARNING.
  --start-date START_DATE
                        (Required) Start downloading data from this date. E.g.: 2019-01-24 00:00:00
  --end-date END_DATE   Download data up to this date. E.g.: 2020-05-30 00:00:00.
                        Default: now.
  --output-dir OUTPUT_DIR
                        The data directory to store the output CSV files.
                        Default: the current directory.
  --timeframe {1m,3m,5m,15m,30m,1h,2h,4h,6h,8h,12h,1d,3d,1w,1M}
                        The frequency of the OHLCV data to be downloaded.
                        Default: 1h.
```

Here is an example of how to download 1-minutes candlestick data for BTC/USDT and ETH/USDT from 18th July 2022 to 20th July 2022:

```console
$ binance-klines --start-date "2022-07-18 00:00:00" \
    --end-date "2022-07-20 23:59:00" --timeframe '1m' --output-dir .data/ \
    --symbols BTC/USDT ETH/USDT
```

### As a Python module

```py
import asyncio
import datetime

from binance_klines import BinanceKLinesDownloader

async def main():
    downloader = BinanceKLinesDownloader()
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

## Tests

Tests are written using `pytest`. To test compatibility among several Python versions, install the dev dependencies using Poetry and run tests using tox:

```console
$ poetry install --with dev
$ tox
```
