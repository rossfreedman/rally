import re


def normalize_series_for_storage(series_str):
    """
    Normalizes a series string to the storage format: "Chicago X"

    Examples:
    - "Chicago - 22" -> "Chicago 22"
    - "Chicago: 22" -> "Chicago 22"
    - "Chicago 3.5(b)" -> "Chicago 35"

    Args:
        series_str (str): The series string to normalize

    Returns:
        str: The normalized series string
    """
    if not series_str:
        return ""

    # Remove any special characters and normalize spacing
    series = series_str.strip()

    # Extract the base name (e.g., "Chicago") and the number
    parts = re.split(r"[-:\s]+", series)
    if len(parts) < 2:
        return series_str  # Return original if can't parse

    base_name = parts[0]
    # Extract all numbers from the remaining parts
    numbers = "".join(re.findall(r"\d+", "".join(parts[1:])))

    return f"{base_name} {numbers}"


def normalize_series_for_display(series_str):
    """
    Normalizes a series string to the display format: "Chicago - X"

    Examples:
    - "Chicago 22" -> "Chicago - 22"
    - "Chicago: 22" -> "Chicago - 22"
    - "Chicago 3.5(b)" -> "Chicago - 35"

    Args:
        series_str (str): The series string to normalize

    Returns:
        str: The normalized series string
    """
    if not series_str:
        return ""

    # First convert to storage format
    storage_format = normalize_series_for_storage(series_str)

    # Split and rejoin with dash
    parts = storage_format.split(" ")
    if len(parts) < 2:
        return series_str  # Return original if can't parse

    return f"{parts[0]} - {parts[1]}"


def series_match(series1, series2):
    """
    Checks if two series strings match, regardless of format

    Examples:
    - series_match("Chicago 22", "Chicago - 22") -> True
    - series_match("Chicago: 22", "Chicago 22") -> True
    - series_match("Chicago 3.5(b)", "Chicago - 35") -> True

    Args:
        series1 (str): First series string
        series2 (str): Second series string

    Returns:
        bool: True if the series match, False otherwise
    """
    if not series1 or not series2:
        return False

    # Normalize both to storage format for comparison
    norm1 = normalize_series_for_storage(series1)
    norm2 = normalize_series_for_storage(series2)

    return norm1 == norm2


def extract_series_number(series_str):
    """
    Extracts just the numeric part of a series string

    Examples:
    - "Chicago 22" -> "22"
    - "Chicago - 22" -> "22"
    - "Chicago: 22" -> "22"
    - "Chicago 3.5(b)" -> "35"

    Args:
        series_str (str): The series string

    Returns:
        str: The numeric part of the series
    """
    if not series_str:
        return ""

    return "".join(re.findall(r"\d+", series_str))
