import pandas as pd
import json
from pathlib import Path

def main():
    records = []
    crawled_data_dir = Path("./crawled_data").resolve()
    for data_path in crawled_data_dir.rglob("*.jsonl"):
        with open(data_path, 'r') as f:
            records += [json.loads(line) for line in f.readlines()]
    df = pd.DataFrame.from_records(records)
    df = df.drop_duplicates(keep=False)
    df.to_excel("zjw_record_around_shangjia.xlsx")


if __name__ == "__main__":
    main()