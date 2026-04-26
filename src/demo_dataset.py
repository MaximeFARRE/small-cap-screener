from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.services.demo_dataset_service import DEMO_DEFAULT_SEED_PATH, DemoDatasetService


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a reproducible local demo dataset.")
    parser.add_argument(
        "--seed-path",
        type=Path,
        default=DEMO_DEFAULT_SEED_PATH,
        help="CSV seed path for the demo universe",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="append to existing local data instead of resetting the database tables",
    )
    parser.add_argument(
        "--skip-storage-init",
        action="store_true",
        help="skip database initialization before seeding",
    )
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _build_argument_parser().parse_args()

    service = DemoDatasetService()
    summary = service.build_demo_dataset(
        seed_csv_path=args.seed_path,
        reset_existing=not args.keep_existing,
        initialize_storage=not args.skip_storage_init,
    )

    logger = logging.getLogger(__name__)
    logger.info("demo dataset ready")
    logger.info("total_companies=%s", summary.total_companies)
    logger.info("scored_companies=%s", summary.scored_companies)
    logger.info("unscored_companies=%s", summary.unscored_companies)
    logger.info("watchlist_entries=%s", summary.watchlist_entries)
    logger.info("excluded_entries=%s", summary.excluded_entries)
    logger.info("ranking_snapshot_id=%s", summary.ranking_snapshot_id)
    logger.info("top_ranked_tickers=%s", ",".join(summary.top_ranked_tickers))


if __name__ == "__main__":
    main()
