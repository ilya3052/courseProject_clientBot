import logging
import os


def setup_logger():
    log_path = os.path.join(os.path.dirname(__file__), "../logs/client_bot_logs.log")

    logging.basicConfig(
        level=logging.INFO,
        filename=log_path,
        filemode="a",
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="UTF-8"
    )
