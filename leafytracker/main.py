import argparse
import json
import logging
import os
import sys

from leafytracker.const import PROJECT

import leafytracker.discord_webhook as discord_webhook


logger = logging.getLogger(PROJECT.NAME)


def _parse_args(args):
    parser = argparse.ArgumentParser(
        prog=PROJECT.NAME.lower(),
        description="{} v{} - {}".format(
            PROJECT.NAME,
            PROJECT.VERSION,
            PROJECT.DESC,
        ),
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Increases verbosity of logging from INFO to DEBUG levels.",
    )

    return parser.parse_args(args)


def _log_unhandled_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception:
            logger.exception(u"%s has crashed!", PROJECT.NAME)
    
    return wrapper


@_log_unhandled_exceptions
def start(raw_args):
    """Launches the program."""
    # Parse any command line arguments
    args = _parse_args(raw_args)

    # Configure logging
    logging.basicConfig(
        filename="{}.log".format(PROJECT.NAME),
        format="%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG if args.verbose else logging.INFO,
        filemode="a",
    )
    
    # Load config file
    with open("config.json") as config_file:
        config = json.load(config_file)

    # Start the program!
    logger.info("Starting %s %s", PROJECT.NAME, PROJECT.VERSION)

    logger.info("Sending Steam News Comments to Discord...")
    discord_webhook.run(
        config.get("app_ids", set()),
        config.get("user_ids", set()),
        config.get("webhooks", set()),
    )
    logger.info("Stopping %s %s", PROJECT.NAME, PROJECT.VERSION)


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    
    start(sys.argv[1:])
