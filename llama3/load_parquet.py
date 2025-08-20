import os
import sys
from pathlib import Path

# Adjust if you install later: pip install pandas pyarrow
try:
    import pandas as pd
except ImportError:
    print("Missing pandas. Install with: pip install pandas pyarrow")
    sys.exit(1)

PARQUET_PATH = Path(r"Z:\llama3_20250528\llama3\RoGWebQSPData\test-00000-of-00002-9ee8d68f7d951e1f.parquet")

def main(show_rows: int = 5, show_schema: bool = True, to_jsonl: bool = False):
    if not PARQUET_PATH.is_file():
        print(f"File not found: {PARQUET_PATH}")
        return

    # Fast metadata read (no full load)
    try:
        import pyarrow.parquet as pq
        meta = pq.ParquetFile(PARQUET_PATH)
        print(f"Row groups: {meta.num_row_groups}, Rows: {meta.metadata.num_rows}, Columns: {meta.metadata.num_columns}")
        if show_schema:
            print("Schema:")
            print(meta.schema)
    except Exception as e:
        print(f"(Optional) Could not read schema via pyarrow: {e}")

    # Load (if large, you may want to read in row-group chunks instead)
    df = pd.read_parquet(PARQUET_PATH)
    print("\nHead:")
    print(df.head(show_rows))

    print("\nColumn dtypes:")
    print(df.dtypes)

    print(f"\nMemory usage (approx): {df.memory_usage(deep=True).sum()/1024/1024:.2f} MB")

    if to_jsonl:
        out_path = PARQUET_PATH.with_suffix(".jsonl")
        print(f"Writing JSONL to {out_path} ...")
        with out_path.open("w", encoding="utf-8") as f:
            for rec in df.to_dict(orient="records"):
                # If nested objects exist, ensure they are JSON-serializable
                import json
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print("Done.")

if __name__ == "__main__":
    # Optional CLI args: first = rows, second = to_jsonl flag
    rows = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    dump_json = (len(sys.argv) > 2 and sys.argv[2].lower() in {"1", "true", "yes"})
    main(show_rows=rows, to_jsonl=dump_json)