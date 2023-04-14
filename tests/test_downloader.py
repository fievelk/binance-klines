import datetime
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import ccxt.async_support as ccxt
import pytest
import pytz

from binance_klines.downloader import BinanceKLinesDownloader, DownloaderException
from tests.fixtures.klines import klines_batch


@pytest.fixture()
def downloader(klines_batch: list[list]):
    """Return a BinanceKLinesDownloader instance with a mocked exchange."""
    downloader = BinanceKLinesDownloader()

    exchange_mock = AsyncMock(spec=ccxt.binance)
    exchange_mock.fetch_ohlcv.return_value = klines_batch
    downloader.exchange = exchange_mock

    return downloader


@pytest.mark.asyncio
async def test_fetch_ohlcv(downloader):
    """The fetch_ohlcv method returns the klines batches from Binance."""
    start_date = datetime.datetime(2020, 9, 1).replace(tzinfo=pytz.utc)
    start_timestamp = int(start_date.timestamp()) * 1000  # milliseconds
    end_date = datetime.datetime(2020, 9, 2).replace(tzinfo=pytz.utc)
    end_timestamp = int(end_date.timestamp()) * 1000  # milliseconds

    # Just iterate over the async generator to make sure it works
    async for _ in downloader.fetch_ohlcv(
        symbol="BTC/USDT",
        start_date=start_date,
        end_date=end_date,
        timeframe="30m",
    ):
        pass

    downloader.exchange.fetch_ohlcv.assert_called_once_with(
        "BTC/USDT",
        timeframe="30m",
        since=start_timestamp,
        limit=500,
        params={"endTime": end_timestamp},
    )


@pytest.mark.asyncio
async def test_fetch_ohlcv_wrong_timeframe(downloader):
    """The fetch_ohlcv method raises an exception if the timeframe is not supported."""
    start_date = datetime.datetime(2020, 9, 1).replace(tzinfo=pytz.utc)
    start_timestamp = int(start_date.timestamp()) * 1000  # milliseconds
    end_date = datetime.datetime(2020, 9, 2).replace(tzinfo=pytz.utc)
    end_timestamp = int(end_date.timestamp()) * 1000  # milliseconds

    with pytest.raises(DownloaderException):
        # Just
        async for _ in downloader.fetch_ohlcv(
            symbol="BTC/USDT",
            start_date=start_date,
            end_date=end_date,
            timeframe="some-wrong-timeframe",
        ):
            pass

    downloader.exchange.fetch_ohlcv.assert_not_called()
