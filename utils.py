# -*- coding: utf-8 -*-
import logging
import os
from datetime import datetime

logging.basicConfig(format="%(asctime)s %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


def current_time():
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def current_date():
    return datetime.now().astimezone().strftime("%Y-%m-%d")


def ensure_dir(file):
    directory = os.path.abspath(os.path.dirname(file))
    if not os.path.exists(directory):
        os.makedirs(directory)


def write_text_file(full_path: str, content: str) -> None:
    ensure_dir(full_path)
    with open(full_path, "w") as fd:
        fd.write(content)
