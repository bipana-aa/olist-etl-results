"""Extract: read the 9 raw CSV files into DataFrames (the raw files are never changed)."""
import pandas as pd

from .config import FILES, RAW_DIR


def extract(raw_dir=RAW_DIR):
    """Read every CSV in FILES from raw_dir and return {table name: DataFrame}."""
    missing_files = [f for f in FILES.values() if not (raw_dir / f).exists()]
    if missing_files:
        raise FileNotFoundError(f"Put these files in {raw_dir}:\n  " + "\n  ".join(missing_files))

    raw = {name: pd.read_csv(raw_dir / filename) for name, filename in FILES.items()}   # EXTRACT
    print(f"Extracted {len(raw)} files from {raw_dir}")
    return raw
