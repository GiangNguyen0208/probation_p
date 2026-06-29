"""CLI entrypoints for the alert engine.

Supports running the worker, evaluating a specific subject, and
evaluating all subjects.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from .health import run_health_check
from .logging_setup import configure_logging, get_logger
from .settings import get_settings
from .tasks import evaluate_all_alerts, evaluate_subject_alerts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="social-alert-engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("evaluate-all", help="Evaluate all subjects with active rules.")
    subparsers.add_parser(
        "run-worker",
        help="Start a Celery worker (with beat) for periodic evaluation.",
    )
    subparsers.add_parser("health", help="Check health of all dependencies.")

    eval_one = subparsers.add_parser("evaluate-one", help="Evaluate a single subject by UUID.")
    eval_one.add_argument("subject_id", help="UUID of the subject to evaluate")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    settings = get_settings()
    configure_logging(settings.runtime.log_level)
    logger = get_logger("social_alert_engine.main")

    parser = _build_parser()
    args = parser.parse_args(argv)

    command = args.command

    if command == "evaluate-all":
        count = evaluate_all_alerts()
        logger.info("cli.evaluate_all.complete", delivered=count)
        return 0

    if command == "evaluate-one":
        count = evaluate_subject_alerts(args.subject_id)
        logger.info("cli.evaluate_one.complete", subject_id=args.subject_id, delivered=count)
        return 0

    if command == "run-worker":
        logger.info("cli.worker.starting")
        from .celery_app import celery_app  # noqa: F811

        celery_app.worker_main(argv=["worker", "--beat", "-l", settings.runtime.log_level])
        return 0

    if command == "health":
        result = run_health_check()
        json.dump(result, sys.stdout, indent=2)
        print()
        return 0 if result["status"] == "ok" else 1

    parser.error(f"Unknown command: {command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
