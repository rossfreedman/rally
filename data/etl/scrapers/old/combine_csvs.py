import os

import pandas as pd


def get_series_number(series_name):
    print(f"\nDebug: Processing series name: '{series_name}'")
    # Extract the number from series name
    parts = series_name.split()
    if not parts:
        print(f"Debug: Empty series name")
        return -1  # Handle empty series name

    # Get the last part (number)
    number_part = parts[-1]
    print(f"Debug: Series '{series_name}' -> number part: '{number_part}'")

    try:
        num = float(number_part)
        print(f"Debug: Successfully extracted number: {num}")
        return num
    except ValueError:
        print(f"Debug: Could not convert '{number_part}' to number")
        return -1  # Handle non-numeric series names


def combine_csv_files():
    try:
        # Update to correct directory path
        data_dir = os.path.join("Data", "player", "all_players_csvs")
        print(f"\nDebug: Looking for CSV files in: {data_dir}")

        # Check if directory exists
        if not os.path.exists(data_dir):
            print(f"❌ {data_dir} directory not found!")
            return

        # List all files in directory
        all_files = os.listdir(data_dir)
        print(f"Debug: Found {len(all_files)} total files in directory")

        # Filter for CSV files with our naming convention
        csv_files = [
            f for f in all_files if f.endswith(".csv") and f.startswith("Series ")
        ]
        print(f"\nDebug: Found {len(csv_files)} CSV files to process")
        print("Debug: CSV files found:")
        for file in csv_files:
            print(f"  - {file}")

        if not csv_files:
            print("\n❌ No matching CSV files found")
            return

        # Read and combine all CSV files
        dfs = []
        for file in csv_files:
            file_path = os.path.join(data_dir, file)
            try:
                print(f"\nDebug: Reading file: {file}")
                df = pd.read_csv(file_path)
                print(f"Debug: Found {len(df)} rows in {file}")
                print(f"Debug: Sample series names from {file}:")
                print(df["Series"].head().to_string())
                dfs.append(df)
            except Exception as e:
                print(f"Error reading {file}: {e}")
                continue

        if not dfs:
            print("❌ No valid CSV files could be read")
            return

        # Combine all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)
        print(f"\nDebug: Combined total of {len(combined_df)} rows")
        print("Debug: Unique series names in combined data:")
        print(combined_df["Series"].unique())

        # Ensure proper data types
        combined_df["PTI"] = pd.to_numeric(combined_df["PTI"], errors="coerce")
        combined_df["Wins"] = pd.to_numeric(combined_df["Wins"], errors="coerce")
        combined_df["Losses"] = pd.to_numeric(combined_df["Losses"], errors="coerce")

        # Sort by series number and last name
        print("\nDebug: Extracting series numbers for sorting...")
        combined_df["sort_key"] = combined_df["Series"].apply(
            lambda x: get_series_number(x)
        )
        print("\nDebug: Sample of sort keys:")
        print(combined_df[["Series", "sort_key"]].head(10).to_string())

        print(
            "\nDebug: Sorting by series number (descending) and last name (ascending)..."
        )
        combined_df = combined_df.sort_values(
            ["sort_key", "Last Name"], ascending=[False, True]
        )
        combined_df = combined_df.drop(
            "sort_key", axis=1
        )  # Remove the temporary sort column

        print("\nDebug: First 10 rows after sorting:")
        print(combined_df[["Series", "Last Name"]].head(10).to_string())

        # Show distribution of players by series
        print("\nPlayers per series:")
        series_counts = combined_df["Series"].value_counts()
        for series, count in series_counts.items():
            print(f"{series}: {count} players")

        # Remove duplicates if any
        combined_df = combined_df.drop_duplicates()
        print(f"\nDebug: After removing duplicates: {len(combined_df)} rows")

        # Save combined data to Data/player directory
        output_path = os.path.join("Data", "player", "all_players.csv")
        combined_df.to_csv(output_path, index=False)
        print(f"\nCreated: all_players.csv")
        print(f"Total players: {len(combined_df)}")

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        print("Debug: Full error traceback:")
        print(traceback.format_exc())


if __name__ == "__main__":
    combine_csv_files()
