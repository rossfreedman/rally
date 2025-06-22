import csv
import json
import os
import traceback
from datetime import datetime


def csv_to_json(csv_filename, json_filename):
    # List to store the data
    data = []

    try:
        # Read CSV file
        with open(csv_filename, "r") as csvfile:
            # Create CSV reader
            csvreader = csv.DictReader(csvfile)

            # Convert each row to dict and append to data list
            for row in csvreader:
                data.append(row)

        # Write to JSON file
        with open(json_filename, "w") as jsonfile:
            json.dump(data, jsonfile, indent=2)

        print(f"Successfully converted {csv_filename} to {json_filename}")

    except Exception as e:
        print(f"Error converting CSV to JSON: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    # Ask user for the filename (without path)
    user_filename = input(
        "Enter the CSV filename (without path, e.g., 'tennis_matches_20240924.csv'): "
    )

    # Get the data directory path
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    # Create full paths for input and output files
    csv_file = os.path.join(data_dir, user_filename)

    # Create JSON filename by replacing .csv with .json
    json_filename = os.path.splitext(user_filename)[0] + ".json"
    json_file = os.path.join(data_dir, json_filename)

    # Check if the CSV file exists
    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' not found.")
        print(f"Please make sure the file exists in the data directory: {data_dir}")
    else:
        # Convert CSV to JSON
        csv_to_json(csv_file, json_file)
