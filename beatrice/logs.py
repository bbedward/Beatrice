import logging
import sys


def configure() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s;%(levelname)s;%(name)s;%(message)s", "%Y-%m-%d %H:%M:%S %z")
    )
    root.addHandler(handler)
    root.setLevel(logging.INFO)
