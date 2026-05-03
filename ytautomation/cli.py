from __future__ import annotations

import argparse
from pathlib import Path

from ytautomation.core.logging import configure_logging
from ytautomation.orchestrator.job_manager import run_all_jobs
from ytautomation.pipeline import import_jobs, run_job


def main() -> None:
    configure_logging()

    parser = argparse.ArgumentParser(prog="ytautomation")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_import = sub.add_parser("import", help="Import jobs from CSV into runs/<job_id>/00_input")
    p_import.add_argument("--csv", required=True, type=Path)

    p_run = sub.add_parser("run", help="Run a job")
    p_run.add_argument("--job-id", required=True)
    p_run.add_argument("--steps", default="script,audio,timeline,render")
    p_run.add_argument("--force", action="store_true")

    p_run_all = sub.add_parser("run-all", help="Run all pending CSV jobs")
    p_run_all.add_argument("--csv", required=True, type=Path)
    p_run_all.add_argument("--max-retries", type=int, default=3)

    args = parser.parse_args()

    if args.cmd == "import":
        jobs = import_jobs(args.csv)
        for j in jobs:
            print(j.job_id)
        return

    if args.cmd == "run":
        steps = [s.strip() for s in args.steps.split(",") if s.strip()]
        run_job(args.job_id, steps=steps, force=args.force)
        print("done")
        return

    if args.cmd == "run-all":
        result = run_all_jobs(args.csv, max_retries=args.max_retries)
        print(result)
        return


if __name__ == "__main__":
    main()
