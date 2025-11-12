#!/usr/bin/env python3
# export_marketbrain_csv.py

import sys
import tempfile
from staking_analysis import main as run_staking
from io import StringIO

if __name__ == "__main__":
    symbol = sys.argv[1].upper()
    start = sys.argv[2]
    end = sys.argv[3]

    # We built argv to run staking_analysis in CSV mode
    sys.argv = [
        "staking_analysis.py",
        "--chains", symbol,
        "--from", start,
        "--to", end,
        "--format", "csv"
    ]

    # Capture CSV output
    buffer = StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer

    try:
        run_staking()
    finally:
        sys.stdout = old_stdout

    csv_text = buffer.getvalue()

    # Save to temporary file
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    tmp_file.write(csv_text.encode("utf-8"))
    tmp_file.close()

    # ✅ Print file path for Electron
    print(tmp_file.name)