import pandas as pd


def transform(file_path: str) -> None:
    df = pd.read_excel(file_path)
    
    with open("./transformed.md", "w") as f:
        header = df.columns
        for index, row in df.iterrows():
            f.write(f"# {header[0]}: {row.iloc[0]}\n")
            for index, item in enumerate(row):
                f.write(f"{header[index]}: {item}\n\n")
            f.write("\n\n")

def transform2texttable(df: pd.DataFrame) -> str:
    text_table = ""
    header = df.columns
    text_table += f"| {' | '.join(header)} |\n"
    text_table += f"| {' | '.join(['---' for _ in header])} |\n"
    for index, row in df.iterrows():
        text_table += f"| {' | '.join(row.astype(str))} |\n"

    return text_table

if __name__ == "__main__":
    import sys
    df = pd.read_excel(sys.argv[1])
    print(transform2texttable(df))