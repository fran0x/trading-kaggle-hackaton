import argparse

import numpy as np
import pandas as pd


def main(args: argparse.Namespace):
    """Randomly generate a solution file for the trading competition.
    The solution file contains the test file with a Usage column.
    Usage column is used to create Public and Private scores and also to define Ignored rows."""

    # Round the ratios to 2 decimal places to avoid floating point errors
    assert round(args.public_ratio + args.private_ratio + args.ignored_ratio, 2) == 1., \
        "Public, Private and Ignored ratios must sum to 1."

    # Read the test file
    test_df = pd.read_csv(args.test_file)

    # Generate a random solution
    test_df["Usage"] = np.random.choice(
        ["Public", "Private", "Ignored"],
        size=len(test_df),
        p=[args.public_ratio, args.private_ratio, args.ignored_ratio]
    )

    # Save the solution to a CSV file
    test_df.to_csv(args.output_file, index=False)
    print(f"Solution saved to {args.output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a random solution file for the trading competition.")
    parser.add_argument("test_file", help="Path to the test file.")
    parser.add_argument("output_file", help="Path to save the solution file.")
    parser.add_argument("--public-ratio", type=float, default=0.3, help="Ratio of Public usage in the solution file.")
    parser.add_argument("--private-ratio", type=float, default=0.6, help="Ratio of Private usage in the solution file.")
    parser.add_argument("--ignored-ratio", type=float, default=0.1, help="Ratio of Ignored usage in the solution file.")
    args = parser.parse_args()

    main(args)