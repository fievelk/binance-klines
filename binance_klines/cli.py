"""Synchronous downloader script."""

import argparse
import asyncio
import datetime
import logging
import os
from pathlib import Path

import pytz

from binance_klines import constants, utils
from binance_klines.downloader import BinanceKLinesDownloader, DownloaderException

logging.basicConfig(format="[%(levelname)s] %(message)s")
LOGGER = logging.getLogger(__name__)

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"  # e.g. 2019-11-16 23:16:15


@utils.timeit
async def run_downloader(symbols, start_date, end_date, timeframe, output_dir):
    downloader = BinanceKLinesDownloader(logger=LOGGER)
    # TODO: move in the downloader class?
    binance_markets = await downloader.get_markets()
    available_symbols = list(binance_markets)
    # Check if all symbols are available on Binance
    missing_symbols = set(symbols) - set(available_symbols)
    if missing_symbols:
        raise DownloaderException(f"Some symbols are not available on Binance: {missing_symbols}.")

    await downloader.fetch_klines(symbols, start_date, end_date, timeframe)


def _ask_confirmation() -> bool:
    proceed = input("The output folder already exists. Continue? [y/n] ")
    if proceed.lower() in ("y", "yes"):
        return True

    return False


def _check_dir_path(path: str) -> str:
    """Check if path is a valid directory path."""

    if Path(path).exists():
        if _ask_confirmation():
            return path

        raise argparse.ArgumentTypeError(f"{path} already exists.")

    return path


def _convert_to_datetime(date_str: str) -> datetime.datetime:
    """Convert a string to a datetime object and add UTC timezone."""
    try:
        return datetime.datetime.strptime(date_str, DATE_FORMAT).replace(tzinfo=pytz.utc)
    except ValueError:
        msg = f"Not a valid date: '{date_str}'. Expected format is {DATE_FORMAT}."
        raise argparse.ArgumentTypeError(msg)


def parse_cli_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase output verbosity. -v: DEBUG. Default: INFO.",
    )
    parser.add_argument(
        "symbols",
        nargs="+",
        help="The list of currencies whose OHLCV will be fetched.",
    )
    parser.add_argument(
        "--start-date",
        required=True,
        help="Start downloading data from this date. E.g.: 2019-01-24 00:00:00",
        type=_convert_to_datetime,
    )
    parser.add_argument(
        "--end-date",
        default=datetime.datetime.now(pytz.utc).strftime(DATE_FORMAT),
        help="Download data up to this date. E.g.: 2020-05-30 00:00:00. Default: now.",
        type=_convert_to_datetime,
    )
    parser.add_argument(
        "--output-dir",
        type=_check_dir_path,
        default=Path.cwd(),
        help="The data directory to store the output CSV files. Default: the current directory.",
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="1h",
        choices=constants.AVAILABLE_TIMEFRAMES,
        help="The frequency of the OHLCV data to be downloaded. Default: 1h.",
    )

    return parser.parse_args()


def _configure_logger(verbosity_level: int):
    """Configure logging levels.

    Args:
        verbosity_level: The number of times the -v flag has been passed.
            0: INFO, 1: DEBUG.
    """
    loglevels = [logging.INFO, logging.DEBUG]
    loglevel = loglevels[min(verbosity_level, len(loglevels) - 1)]  # Cap to the number of levels
    LOGGER.setLevel(loglevel)


def main():
    arguments = parse_cli_arguments()
    _configure_logger(arguments.verbose)

    asyncio.run(
        run_downloader(
            symbols=arguments.symbols,
            start_date=arguments.start_date,
            end_date=arguments.end_date,
            output_dir=arguments.output_dir,
            timeframe=arguments.timeframe,
        )
    )


if __name__ == "__main__":
    main()
