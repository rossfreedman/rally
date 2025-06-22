import json
import os
from datetime import datetime, timedelta


def get_practice_info():
    print("\nEnter Tennaqua - 22 Practice Schedule")
    print("-----------------------------------")

    # Get first practice date
    while True:
        try:
            first_date = input("Enter first practice date (MM/DD/YYYY): ")
            first_date_obj = datetime.strptime(first_date, "%m/%d/%Y")
            break
        except ValueError:
            print("Invalid date format. Please use MM/DD/YYYY")

    # Get practice day
    while True:
        day = input("Enter practice day (e.g., Monday): ").strip()
        if day.lower() in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            break
        print("Invalid day. Please enter a valid day of the week.")

    # Get practice time
    while True:
        try:
            time = input("Enter practice time (e.g., 6:30 pm): ").strip()
            # Validate the time format
            datetime.strptime(time, "%I:%M %p")
            break
        except ValueError:
            print("Invalid time format. Please use format like '6:30 pm'")

    return first_date_obj, day, time


def update_schedule_with_practices(first_date, day, time):
    schedule_file = "data/tennis_schedule_20250418.json"

    # Read existing schedule
    with open(schedule_file, "r") as f:
        schedule = json.load(f)

    # Get the end of season date from the filename (20250418)
    end_date = datetime(2025, 4, 18)

    # Convert day name to number (0=Monday, 6=Sunday)
    day_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    target_weekday = day_map[day.lower()]

    # Start from the first practice date
    current_date = first_date

    # Add practice entries until end of season
    while current_date <= end_date:
        # If current date is the target weekday, add practice
        if current_date.weekday() == target_weekday:
            # Add the practice entry
            practice_entry = {
                "date": current_date.strftime("%m/%d/%Y"),
                "time": time,
                "Practice": "",
            }
            # Insert at the beginning of the schedule
            schedule.insert(0, practice_entry)

        # Move to next day
        current_date += timedelta(days=1)

    # Sort the schedule by date and time
    schedule.sort(
        key=lambda x: (
            datetime.strptime(x["date"], "%m/%d/%Y"),
            datetime.strptime(x["time"], "%I:%M %p"),
        )
    )

    # Save updated schedule
    with open(schedule_file, "w") as f:
        json.dump(schedule, f, indent=4)

    print(
        f"\nAdded {len([x for x in schedule if 'Practice' in x])} practice entries to the schedule."
    )


def main():
    print("Tennis Practice Schedule Setup - Tennaqua - 22")
    print("--------------------------------------------")

    # Get practice information
    first_date, day, time = get_practice_info()

    # Update the schedule with practices
    update_schedule_with_practices(first_date, day, time)

    print("\nSchedule updated successfully with Tennaqua practice times!")


if __name__ == "__main__":
    main()
