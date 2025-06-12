import pytesseract
from PIL import Image
import re


def extract_standings_from_image(image_path):
    """
    Extracts and parses standings data from a PNG image using OCR.
    Args:
        image_path (str): Path to the PNG image file.
    Returns:
        list[dict]: List of standings rows as dictionaries.
    """
    # Load image
    img = Image.open(image_path)
    # Run OCR
    raw_text = pytesseract.image_to_string(img)
    print("--- OCR Output ---")
    print(raw_text)
    print("------------------\n")

    # Attempt to parse table rows from OCR output
    # This regex assumes rows are separated by newlines and columns by whitespace or tabs
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    if not lines:
        return []

    # Improved parsing logic
    # Find the header row (look for keywords)
    header_idx = None
    for i, line in enumerate(lines):
        if re.search(r'Series|Place|Points|Played|Avg', line, re.IGNORECASE):
            header_idx = i
            break
    if header_idx is None:
        print("Could not find header row. Please check OCR output above.")
        return []

    # Extract header and clean it up
    header_line = lines[header_idx]
    # Remove any non-alphanumeric characters at the start/end
    header_line = header_line.strip('|} ').replace(':', '')
    # Split header by whitespace
    header = re.split(r'\s+', header_line)

    # Data rows follow the header, until a summary/note line is found
    data_rows = []
    for line in lines[header_idx+1:]:
        # Stop at summary or note lines
        if re.match(r'(Total|Playoff|Ast|Mugs|\*|\()', line):
            break
        # Clean and split row
        row = line.strip('|} ').replace(':', '')
        cols = re.split(r'\s+', row)
        # Only include rows with the correct number of columns
        if len(cols) == len(header):
            data_rows.append(cols)

    if not data_rows:
        print("No valid data rows found. Please check OCR output above.")
        return []

    # Build list of dicts
    standings = [dict(zip(header, row)) for row in data_rows]

    # Clean up column names
    col_map = {
        'Series': 'Series',
        'Place': 'Place',
        '#Teams|': 'Teams',
        'Points': 'Points For',
        'Against': 'Points Against',
        'Played': 'Matches Played',
        'Avg': 'Points Avg',
        '1st': '1st Place',
    }
    cleaned_standings = []
    for row in standings:
        cleaned_row = {col_map.get(k, k): v for k, v in row.items()}
        cleaned_standings.append(cleaned_row)
    return cleaned_standings


def main():
    """Extract and print standings from clubstats.png."""
    image_path = 'clubstats.png'
    standings = extract_standings_from_image(image_path)
    print("Parsed Standings Data:")
    for row in standings:
        print(row)

if __name__ == "__main__":
    main() 