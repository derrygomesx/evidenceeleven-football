
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/hudl/open-data/master/data"
OUTPUT = Path("backend/data/statsbomb")
MAX_RETRIES = 3


def download_json(url, destination):
    """Download and validate a JSON file, retrying temporary failures."""

    destination.parent.mkdir(parents=True, exist_ok=True)

    # Reuse existing files if they contain valid JSON
    if destination.exists():
        try:
            with destination.open("r", encoding="utf-8") as file:
                json.load(file)
            return "already_exists"
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"  Existing file is invalid; redownloading {destination.name}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "EvidenceX1-Data-Downloader"}
            )

            with urllib.request.urlopen(request, timeout=45) as response:
                data = response.read()

            parsed = json.loads(data)

            # Save only after the JSON has been validated
            temporary_path = destination.with_suffix(".tmp")
            temporary_path.write_bytes(data)
            temporary_path.replace(destination)

            return "downloaded"

        except urllib.error.HTTPError as error:
            # A 404 is normally permanent, so don't retry it
            if error.code == 404:
                return "not_found"

            message = f"HTTP {error.code}"

        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            OSError,
        ) as error:
            message = str(error)

        if attempt < MAX_RETRIES:
            wait_seconds = attempt * 2
            print(
                f"  Attempt {attempt}/{MAX_RETRIES} failed: {message}. "
                f"Retrying in {wait_seconds}s..."
            )
            time.sleep(wait_seconds)
        else:
            print(f"  Failed after {MAX_RETRIES} attempts: {message}")

    return "failed"


def main():
    matches_path = OUTPUT / "matches" / "55" / "282.json"
    matches_url = f"{BASE_URL}/matches/55/282.json"

    result = download_json(matches_url, matches_path)

    if result in ("failed", "not_found"):
        print("Could not download Euro 2024 match metadata.")
        print("Check your internet connection and try again.")
        return

    with matches_path.open("r", encoding="utf-8") as file:
        matches = json.load(file)

    print(f"\nEuro 2024 matches listed: {len(matches)}")

    counts = {
        "events": {"downloaded": 0, "existing": 0, "failed": 0, "missing": 0},
        "lineups": {"downloaded": 0, "existing": 0, "failed": 0, "missing": 0},
    }

    failures = []

    for index, match in enumerate(matches, start=1):
        match_id = match["match_id"]
        print(f"\n[{index}/{len(matches)}] Match ID: {match_id}")

        for category in ("events", "lineups"):
            url = f"{BASE_URL}/{category}/{match_id}.json"
            destination = OUTPUT / category / f"{match_id}.json"

            result = download_json(url, destination)

            if result == "downloaded":
                counts[category]["downloaded"] += 1
            elif result == "already_exists":
                counts[category]["existing"] += 1
            elif result == "not_found":
                counts[category]["missing"] += 1
                failures.append((match_id, category, "HTTP 404"))
                print(f"  No {category} file in the repository.")
            else:
                counts[category]["failed"] += 1
                failures.append((match_id, category, "Download failed"))

    print("\n========== DOWNLOAD SUMMARY ==========")
    print(f"Matches listed: {len(matches)}")

    for category, stats in counts.items():
        total = stats["downloaded"] + stats["existing"]
        print(f"\n{category.upper()}:")
        print(f"  Newly downloaded: {stats['downloaded']}")
        print(f"  Already available: {stats['existing']}")
        print(f"  Valid files available: {total}")
        print(f"  Missing from repository: {stats['missing']}")
        print(f"  Download failures: {stats['failed']}")

    if failures:
        print("\nFiles needing attention:")
        for match_id, category, reason in failures:
            print(f"  {category}/{match_id}.json — {reason}")

    print("\nDownload check complete.")


if __name__ == "__main__":
    main()
