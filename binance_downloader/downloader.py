"""Binance data downloader.

Fetch OHLCV klines from Binance.

"""
import datetime
import logging
from pathlib import Path

import ccxt.async_support as ccxt  # link against the asynchronous version of ccxt
import pytz
from ccxt.base.errors import BadSymbol

from binance_downloader import settings, utils
from binance_downloader.constants import AVAILABLE_TIMEFRAMES
from binance_downloader.utils import timeit

LOGGER = logging.getLogger(__name__)


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
        LOGGER.info("Loading markets from Binance...")
        return self.exchange.load_markets()
        LOGGER.info("Markets loaded.")

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
