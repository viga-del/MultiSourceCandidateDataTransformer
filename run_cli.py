"""
run_cli.py
==========
Command-line entry point for the Candidate Data Transformer.

This replaces the FastAPI/browser workflow (uvicorn + Swagger UI at /docs).
Run everything directly from VS Code's terminal (or the "Run" button) and
the final candidate JSON is printed to the console and saved under
output/profiles/.

USAGE
-----
    python run_cli.py --files input/csv/candidate.csv input/json/candidate.json input/notes/john_notes.txt
    python run_cli.py --files input/resumes/john.pdf --github johndoe
    python run_cli.py --files input/csv/candidate.csv --fields full_name emails skills

If --files / --github / --linkedin-text are all omitted, the script falls
back to auto-discovering every file under input/csv, input/json,
input/notes, input/resumes, input/uploads.
"""

import argparse
import glob
import json
import os
import sys

from app.services.transformation_service import TransformationService


def discover_default_files() -> list:
    """Find candidate input files automatically under the input/ folder."""
    search_dirs = [
        "input/csv",
        "input/json",
        "input/notes",
        "input/resumes",
        "input/uploads",
    ]
    found = []
    for d in search_dirs:
        if os.path.isdir(d):
            for pattern in ("*.csv", "*.json", "*.pdf", "*.docx", "*.txt"):
                found.extend(sorted(glob.glob(os.path.join(d, pattern))))
    return found


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the Candidate Data Transformer pipeline from the command line."
    )
    parser.add_argument(
        "--files", "-f", nargs="*", default=None,
        help="Paths to input files (PDF, DOCX, CSV, JSON, TXT). "
             "If omitted, auto-discovers files under input/.",
    )
    parser.add_argument(
        "--github", "-g", default=None,
        help="GitHub username to fetch and merge in.",
    )
    parser.add_argument(
        "--linkedin-text", default=None,
        help="Raw LinkedIn profile text to parse and merge in.",
    )
    parser.add_argument(
        "--fields", nargs="*", default=None,
        help="Specific output fields to project (defaults to projection.json config).",
    )
    parser.add_argument(
        "--config", "-c", default=None,
        help="Path to a runtime projection config JSON (select/rename/normalize fields, "
             "toggle confidence/provenance, set on_missing behavior). "
             "See app/config/custom_projection_example.json. Overrides --fields.",
    )
    parser.add_argument(
        "--no-save", action="store_true",
        help="Don't write the result to output/profiles/ (print only).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    file_paths = args.files
    if file_paths is None:
        file_paths = discover_default_files()
        if file_paths:
            print(f"[info] No --files given; auto-discovered {len(file_paths)} file(s) under input/:")
            for fp in file_paths:
                print(f"         - {fp}")

    if not file_paths and not args.github and not args.linkedin_text:
        print("[error] No input sources found. Pass --files, --github, and/or --linkedin-text.")
        sys.exit(1)

    service = TransformationService()

    projection_config = None
    if args.config:
        try:
            with open(args.config, "r", encoding="utf-8") as f:
                projection_config = json.load(f)
        except Exception as e:
            print(f"[error] Could not read config file '{args.config}': {e}")
            sys.exit(1)

    try:
        result = service.transform_from_files(
            file_paths=file_paths,
            github_username=args.github,
            linkedin_text=args.linkedin_text,
            projection_fields=args.fields,
            projection_config=projection_config,
            save_output=not args.no_save,
        )
    except ValueError as e:
        print(f"[error] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[error] Transformation failed: {e}")
        raise

    print("\n" + "=" * 60)
    print("FINAL CANDIDATE PROFILE")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if not args.no_save:
        candidate_id = result.get("candidate_id", "unknown")
        print(f"\n[info] Saved to output/profiles/{candidate_id}.json")


if __name__ == "__main__":
    main()
