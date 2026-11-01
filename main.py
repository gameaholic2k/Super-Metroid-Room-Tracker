import sys
import gui
import logging
import argparse
from tendo import singleton

def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),          # Print to console
            logging.FileHandler("app.log")    # Write to a file
        ]
    )
if __name__ == "__main__":
    try:
        single_instance = singleton.SingleInstance()
    except singleton.SingleInstanceException:
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Super Metroid room time tracker")
    parser.add_argument("-eo", "--extra_options", action="store_true", help="Enables extra options.")
    args = parser.parse_args()

    configure_logging()
    # Get main logger and start application
    logger = logging.getLogger(__name__)
    logger.info("Application start.")
    gui.MainApplication(args.extra_options)