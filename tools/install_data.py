import argparse
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


COMPETITION = "store-sales-time-series-forecasting"
FILES = (
    "train.csv",
    "test.csv",
    "stores.csv",
    "oil.csv",
    "holidays_events.csv",
    "transactions.csv",
    "sample_submission.csv",
)
DEFAULT_DESTINATION = Path(__file__).resolve().parents[1] / "data" / "raw"


def install(destination: Path, force: bool = False) -> None:
    destination = destination.resolve()
    needed = [
        name for name in FILES
        if force or not (destination / name).is_file()
        or (destination / name).stat().st_size == 0
    ]
    if not needed:
        print(f"All {len(FILES)} CSV files are already present in {destination}.")
        return

    if importlib.util.find_spec("kaggle") is None:
        raise RuntimeError(
            "Kaggle is not installed. Run: python -m pip install -r requirements.txt"
        )

    with tempfile.TemporaryDirectory(prefix="yumeko-data-") as temporary:
        subprocess.run(
            [
                sys.executable, "-m", "kaggle", "competitions", "download",
                "-c", COMPETITION, "-p", temporary,
            ],
            check=True,
        )
        archive_path = Path(temporary) / f"{COMPETITION}.zip"
        with zipfile.ZipFile(archive_path) as archive:
            # Only copy the expected filenames; never extract arbitrary ZIP paths.
            for name in needed:
                info = archive.getinfo(name)
                if info.is_dir() or info.file_size == 0:
                    raise RuntimeError(f"Archive contains an empty or invalid {name}.")
            staged = Path(temporary) / "extracted"
            staged.mkdir()
            for name in needed:
                with archive.open(name) as source, (staged / name).open("wb") as target:
                    shutil.copyfileobj(source, target)

        destination.mkdir(parents=True, exist_ok=True)
        for name in needed:
            shutil.copyfile(staged / name, destination / name)
            print(f"Installed {name}")
    print(f"Data ready in {destination}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination", type=Path, default=DEFAULT_DESTINATION,
        help="Output directory (default: project data/raw).",
    )
    parser.add_argument(
        "--force", action="store_true", help="Download and replace existing CSVs.",
    )
    args = parser.parse_args()
    try:
        install(args.destination, args.force)
    except subprocess.CalledProcessError:
        print(
            "Kaggle download failed. Check your connection and Kaggle credentials, "
            "and accept the competition rules on its website before retrying.",
            file=sys.stderr,
        )
        return 1
    except (OSError, RuntimeError, KeyError, zipfile.BadZipFile) as error:
        print(f"Data installation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
