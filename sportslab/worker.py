"""Dedicated tracking process. Run alongside the web service with the same data directory."""
import logging
import time

from .store import Store
from .locking import pipeline_lock
from .model import Predictor
from .tracking import capture
from .ingest import Importer


def cycle(store):
    # The OS lock prevents overlap with imports/training or another worker.
    with pipeline_lock():
        importer=Importer(store)
        importer.job('football:upcoming',importer.fixtures)
        store.settle()
        return capture(store,Predictor(store))


def main():
    logging.basicConfig(level=logging.INFO)
    store=Store()
    while True:
        try:logging.info('Tracking cycle: %s',cycle(store))
        except Exception:
            logging.exception('Tracking cycle failed; retrying in ten minutes')
        time.sleep(600)


if __name__=='__main__':main()
