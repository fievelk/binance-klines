"""Binance data downloader.

Fetch OHLCV klines from Binance.

"""
import datetime
from pathlib import Path

import ccxt.async_support as ccxt  # link against the asynchronous version of ccxt
import pytz
from ccxt.base.errors import BadSymbol

from binance_downloader import settings, utils
from binance_downloader.utils import timeit


class OHLCVDownloaderException(Exception):
    """Exception raised by the BinanceOHLCVDownloader class."""


class BinanceOHLCVDownloader:
    """Downloader for OHLCV klines.

    Args:
        limit (int, optional): Number of klines to fetch per request. Defaults to 500.
    """

    def __init__(self, limit: int = 500) -> None:
        self.limit = limit
        self._markets = None

        self._instantiate_exchange()

    async def fetch_ohlcv(
        self,
        symbol: str,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        timeframe: str = "1h",
    ):
        """Download OHCLV data (klines).

        Args:
            symbol (str): Symbol to download (e.g.: BTC/USDT). Must be a valid symbol for Binance.
            start_date (datetime.datetime): Start date (UTC timezone)
            end_date (datetime.datetime): End date (UTC timezone)
            timeframe (str, optional): Timeframe to download. Defaults to "1h".

        Yields:
            List[int]: a list of OHLCV lines. Structure of each kline:
                [
                    1504541580000, // UTC timestamp in milliseconds, integer
                    4235.4,        // (O)pen price, float
                    4240.6,        // (H)ighest price, float
                    4230.0,        // (L)owest price, float
                    4230.7,        // (C)losing price, float
                    37.72941911    // (V)olume (in terms of the base currency), float
                ]

        """
        assert start_date.tzinfo == pytz.utc, "Dates must be in UTC timezone"
        assert end_date.tzinfo == pytz.utc, "Dates must be in UTC timezone"

        # Convert UTC dates to timestamps in milliseconds (needed by Binance API)
        start_date_timestamp = int(start_date.timestamp()) * 1000  # Milliseconds
        end_date_timestamp = int(end_date.timestamp()) * 1000  # Milliseconds

        if self.exchange.has["fetchOrders"]:
            since = start_date_timestamp
            i = 0
            while since < end_date_timestamp:
                i += 1
                print(f"{symbol} - Iteration {i}", end="\r")
                klines_batch = await self._fetch_ohlcv(
                    symbol, timeframe=timeframe, start=since, end=end_date_timestamp
                )

                if klines_batch:
                    # Get the last timestamp and make another request from it
                    # NOTE: we increase by 1 to avoid duplicates
                    since = klines_batch[len(klines_batch) - 1][0] + 1
                else:
                    break

                yield klines_batch

            print()

    def get_markets(self):
        """Get the list of markets (symbols) available on Binance."""
        return self.exchange.load_markets()

    def _instantiate_exchange(self):
        self.exchange = ccxt.binance(
            {
                "apiKey": settings.BINANCE_API_KEY,
                "secret": settings.BINANCE_API_SECRET,
                "timeout": 30000,
                "enableRateLimit": True,
            }
        )

    def _fetch_ohlcv(self, symbol, start, end, timeframe="1h"):
        """Call the GET /api/v3/klines method of Binance API."""

        # Binance has a specific end time parameter. This makes the class not generic!
        params = {"endTime": end}  # TODO: it seems like this does not work

        try:
            return self.exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                since=start,
                limit=self.limit,
                params=params,
            )
        except BadSymbol as ex:
            raise OHLCVDownloaderException(ex) from ex


@timeit
async def main():
    start_date = datetime.datetime(2020, 9, 1).replace(
        tzinfo=pytz.utc
    )  #  Add UTC timezone
    end_date = datetime.datetime(2021, 9, 1).replace(
        tzinfo=pytz.utc
    )  #  Add UTC timezone
    symbols = ["BTC/USDT", "ETH/USDT", "LTC/USDT"]
    TIMEFRAMES = [
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
        "3d",
        "1w",
        "1M",
    ]
    timeframe = TIMEFRAMES[4]

    downloader = BinanceOHLCVDownloader()
    binance_markets = await downloader.get_markets()
    available_symbols = list(binance_markets)

    # Check if all symbols are available on Binance. If not, raise an exception showing the missing symbols
    missing_symbols = set(symbols) - set(available_symbols)
    if missing_symbols:
        raise OHLCVDownloaderException(
            f"Some symbols are not available on Binance: {missing_symbols}."
        )

    try:
        await asyncio.gather(
            *[
                _download_single_symbol(
                    downloader, symbol, start_date, end_date, timeframe
                )
                for symbol in symbols
            ]
        )
        # This is the synchronous version (if you want to compare the performance)
        # for symbol in symbols:
        #     await _download_single_symbol(downloader, symbol, start_date, end_date, timeframe)
    finally:
        # Binance requires to release all resources with an explicit call to the .close()
        # coroutine when you don't need the exchange instance anymore (at the end of your a
        # sync coroutine).
        await downloader.exchange.close()


async def _download_single_symbol(downloader, symbol, start_date, end_date, timeframe):
    print(f"Downloading symbol {symbol}")
    output_filename = Path(f"{symbol.replace('/', '_')}-{timeframe}.csv")
    try:
        async for batch in downloader.fetch_ohlcv(
            symbol, start_date, end_date, timeframe=timeframe
        ):
            utils.write_data_to_file(batch, output_filename)
    except OHLCVDownloaderException as ex:
        print(ex)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
