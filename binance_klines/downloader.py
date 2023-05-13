"""Binance data downloader.

Fetch OHLCV klines from Binance.

"""
import asyncio
import datetime
import logging
from pathlib import Path

import ccxt.async_support as ccxt  # link against the asynchronous version of ccxt
import pytz
from ccxt.base.errors import BadSymbol

from binance_klines import utils
from binance_klines.constants import AVAILABLE_TIMEFRAMES


class DownloaderException(Exception):
    """Exception raised by the BinanceKLinesDownloader class."""


class BinanceKLinesDownloader:
    """Downloader for OHLCV klines.

    Args:
        limit (int, optional): Number of klines to fetch per request. Defaults to 500.
        output_dir (str | Path, optional): Directory where to store the downloaded data.
        logger (logging.Logger, optional): Logger to use. Defaults to None.
    """

    def __init__(
        self, limit: int = 500, output_dir: str | Path = ".", logger: logging.Logger | None = None
    ) -> None:
        self.limit = limit
        self.output_dir = Path(output_dir)
        self._markets = None
        self._logger = logger or logging.getLogger(__name__)

        self._instantiate_exchange()

    async def fetch_klines(
        self,
        symbols: list[str],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        timeframe: str = "1h",
    ):
        """Download OHCLV data (klines).

        Args:
            symbols (list[str]): Symbols to download (e.g.: BTC/USDT). Must be valid symbols
                for Binance.
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
        start_date = self._preprocess_date(start_date)
        end_date = self._preprocess_date(end_date)

        assert start_date.tzinfo == pytz.utc, "Dates must be in UTC timezone"
        assert end_date.tzinfo == pytz.utc, "Dates must be in UTC timezone"

        if timeframe not in AVAILABLE_TIMEFRAMES:
            raise DownloaderException(
                f"Invalid timeframe: {timeframe}. Available timeframes: {AVAILABLE_TIMEFRAMES}"
            )

        try:
            results = await asyncio.gather(
                *[
                    self._fetch_and_store_klines_for_symbol(
                        symbol, start_date, end_date, timeframe
                    )
                    for symbol in symbols
                ]
            )
            # This is the synchronous version (if you want to compare the performance)
            # for symbol in symbols:
            #     await _fetch_and_store_klines_for_symbol(downloader, symbol, start_date, end_date, timeframe)
        finally:
            # Binance requires to release all resources with an explicit call to the .close()
            # coroutine when you don't need the exchange instance anymore (at the end of your a
            # sync coroutine).
            await self.exchange.close()

        return results

    async def _fetch_and_store_klines_for_symbol(self, symbol, start_date, end_date, timeframe):
        """Download and store OHCLV data (klines) for a single symbol."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_filename = self.output_dir / f"{symbol.replace('/', '_')}-{timeframe}.csv"

        batches = []
        try:
            async for batch in self._fetch_ohlcv_for_symbol(
                symbol, start_date, end_date, timeframe=timeframe
            ):
                batches.append(batch)
                utils.write_data_to_file(batch, output_filename)
        except DownloaderException as ex:
            self._logger.error("An error occurred while downloading %s: %s", symbol, ex)

        return batches

    async def _fetch_ohlcv_for_symbol(
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
        # Convert UTC dates to timestamps in milliseconds (needed by Binance API)
        start_date_timestamp = int(start_date.timestamp()) * 1000  # Milliseconds
        end_date_timestamp = int(end_date.timestamp()) * 1000  # Milliseconds

        if self.exchange.has["fetchOrders"]:
            self._logger.info("Download in progress: %s", symbol)
            since = start_date_timestamp
            while since < end_date_timestamp:
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
            self._logger.info("Download finished: %s", symbol)

    def get_markets(self):
        """Get the list of markets (symbols) available on Binance."""
        self._logger.info("Loading markets from Binance...")
        markets = self.exchange.load_markets()
        self._logger.info("Markets loaded.")

        return markets

    def _instantiate_exchange(self):
        self.exchange = ccxt.binance(
            {
                "timeout": 30000,
                "enableRateLimit": True,
            }
        )

    async def _fetch_ohlcv(self, symbol, start, end, timeframe="1h"):
        """Call the GET /api/v3/klines method of Binance API."""

        # Binance has a specific end time parameter. This makes the class not generic!
        params = {"endTime": end}  # TODO: it seems like this does not work

        try:
            return await self.exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                since=start,
                limit=self.limit,
                params=params,
            )
        except BadSymbol as ex:
            raise DownloaderException(ex) from ex

    def _preprocess_date(self, date: datetime.datetime) -> datetime.datetime:
        """Convert a datetime timezone to UTC."""
        if date.tzinfo:
            if int(date.utcoffset().total_seconds()) != 0:
                self._logger.warning("The given date is not in UTC timezone. Converting to UTC.")
                return date.astimezone(pytz.utc)
            else:
                return date

        self._logger.warning("The given date is not timezone aware. Assuming UTC.")

        return date.replace(tzinfo=pytz.utc)
