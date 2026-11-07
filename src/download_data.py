"""Phase 1 - Download a subset of StatsBomb Open Data into data/raw/statsbomb."""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from tqdm import tqdm

from src.config import (
    COMPETITIONS,
    DOWNLOAD_RETRIES,
    DOWNLOAD_WORKERS,
    RAW_DIR,
    STATSBOMB_BASE_URL,
)


def download_file(relative_path: str, overwrite: bool = False) -> Path:
    """Download one file into RAW_DIR, keeping StatsBomb's folder layout.

    Skips files that already exist, so the script can be re-run safely.
    """
    target = RAW_DIR / relative_path
    if target.exists() and not overwrite:
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    url = f"{STATSBOMB_BASE_URL}/{relative_path}"

    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            # Write to a temp file first, then rename: no half-written files if interrupted
            tmp = target.with_suffix(".tmp")
            tmp.write_bytes(response.content)
            tmp.replace(target)
            return target
        except requests.RequestException:
            if attempt == DOWNLOAD_RETRIES:
                raise
            time.sleep(2 ** attempt)


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_match_ids() -> list[int]:
    """Download the competitions + matches files and return the selected match IDs."""
    competitions = load_json(download_file("competitions.json", overwrite=True))
    names = {
        (c["competition_id"], c["season_id"]): f'{c["competition_name"]} {c["season_name"]}'
        for c in competitions
    }

    match_ids = []
    for competition_id, season_id in COMPETITIONS:
        matches = load_json(download_file(f"matches/{competition_id}/{season_id}.json"))
        label = names.get((competition_id, season_id), f"{competition_id}/{season_id}")
        print(f"  {label:<32} {len(matches):>4} matches")
        match_ids.extend(m["match_id"] for m in matches)
    return match_ids


def download_matches(match_ids: list[int]) -> list[str]:
    """Download events + lineups for every match in parallel. Returns files that failed."""
    files = [f"{kind}/{mid}.json" for mid in match_ids for kind in ("events", "lineups")]
    failed = []

    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
        futures = {pool.submit(download_file, f): f for f in files}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading", unit="file"):
            try:
                future.result()
            except Exception:
                failed.append(futures[future])
    return failed


def folder_size_mb(folder: Path) -> float:
    return sum(p.stat().st_size for p in folder.rglob("*.json")) / 1024 ** 2


def main():
    parser = argparse.ArgumentParser(description="Download a StatsBomb Open Data subset")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Only download the first N matches (for a quick test)",
    )
    args = parser.parse_args()

    print("Fetching competition and match lists...")
    match_ids = get_match_ids()
    print(f"Total matches selected: {len(match_ids)}")

    if args.limit:
        match_ids = match_ids[: args.limit]
        print(f"--limit set: downloading only {len(match_ids)} matches")

    failed = download_matches(match_ids)

    n_events = len(list((RAW_DIR / "events").glob("*.json")))
    n_lineups = len(list((RAW_DIR / "lineups").glob("*.json")))
    print("\n----- Download summary -----")
    print(f"Event files  : {n_events}")
    print(f"Lineup files : {n_lineups}")
    print(f"Total size   : {folder_size_mb(RAW_DIR):,.1f} MB")

    if failed:
        print(f"Failed ({len(failed)}) - re-run the script to retry:")
        for f in failed[:20]:
            print("  ", f)
        sys.exit(1)
    print("All files downloaded successfully.")


if __name__ == "__main__":
    main()
