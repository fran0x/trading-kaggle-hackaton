import argparse
import uuid

import pandas as pd


def main(args: argparse.Namespace):
    """Merge multiple CSV files into one."""

    # Read all CSV files into a list of DataFrames
    dataframes = [pd.read_csv(file) for file in args.input_files]

    # Concatenate all DataFrames into one
    merged_df = pd.concat(dataframes, ignore_index=True)

    # Rename real symbol names to generic names
    merged_df["symbol"].replace(
        {
            f"{args.token1}/{args.fiat}": "token_1/fiat",
            f"{args.token2}/{args.fiat}": "token_2/fiat",
            f"{args.token1}/{args.token2}": "token_1/token_2",
        },
        inplace=True
    )

    merged_df["id"] = [str(uuid.uuid4()) for _ in range(len(merged_df))]
    merged_df.set_index("id", inplace=True)

    # Sort by timestamp
    merged_df.sort_values(by="timestamp", inplace=True)

    # Save the merged DataFrame to the output file
    merged_df.to_csv(args.output, index=True)
    print(f"Merged {len(dataframes)} files into {args.output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge multiple CSV files into one.")
    parser.add_argument("input_files", nargs="+", help="Input CSV files to merge.")
    parser.add_argument("--output", required=True, help="Output CSV file path.")
    parser.add_argument("--token1", default="ETH", help="Name of the first token.")
    parser.add_argument("--token2", default="BTC", help="Name of the second token.")
    parser.add_argument("--fiat", default="USDT", help="Name of the fiat token.")
    args = parser.parse_args()

    main(args)