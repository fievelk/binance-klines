import datetime
from unittest.mock import AsyncMock, patch

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
@patch("binance_klines.downloader.write_data_to_file")
async def test_fetch_klines(write_data_to_file_mock, downloader: BinanceKLinesDownloader, klines_batch: list[list]):
    """The fetch_klines method returns the klines batches from Binance."""
    start_date = datetime.datetime(2020, 9, 1).replace(tzinfo=pytz.utc)
    start_timestamp = int(start_date.timestamp()) * 1000  # milliseconds
    end_date = datetime.datetime(2020, 9, 2).replace(tzinfo=pytz.utc)
    end_timestamp = int(end_date.timestamp()) * 1000  # milliseconds

    results = await downloader.fetch_klines(
        symbols=["BTC/USDT"],
        start_date=start_date,
        end_date=end_date,
        timeframe="30m",
    )

    downloader.exchange.fetch_ohlcv.assert_called_once_with(
        "BTC/USDT",
        timeframe="30m",
        since=start_timestamp,
        limit=500,
        params={"endTime": end_timestamp},
    )

    assert results[0][0] == klines_batch
    write_data_to_file_mock.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_klines_wrong_timeframe(downloader: BinanceKLinesDownloader):
    """The fetch_klines method raises an exception if the timeframe is not supported."""
    start_date = datetime.datetime(2020, 9, 1).replace(tzinfo=pytz.utc)
    start_timestamp = int(start_date.timestamp()) * 1000  # milliseconds
    end_date = datetime.datetime(2020, 9, 2).replace(tzinfo=pytz.utc)
    end_timestamp = int(end_date.timestamp()) * 1000  # milliseconds

    with pytest.raises(DownloaderException):
        await downloader.fetch_klines(
            symbols=["BTC/USDT"],
            start_date=start_date,
            end_date=end_date,
            timeframe="some-wrong-timeframe",
        )

    downloader.exchange.fetch_ohlcv.assert_not_called()
