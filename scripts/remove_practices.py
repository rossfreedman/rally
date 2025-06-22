import json

# Read the current schedule
with open("data/leagues/all/schedules.json", "r") as f:
    schedule = json.load(f)

print(f"Original schedule has {len(schedule)} entries")

# Count practice entries before removal
practice_count = sum(1 for entry in schedule if "Practice" in entry)
print(f"Found {practice_count} practice entries to remove")

# Filter out all entries that have a 'Practice' field
filtered_schedule = [entry for entry in schedule if "Practice" not in entry]

print(f"After removal: {len(filtered_schedule)} entries remaining")

# Save the updated schedule
with open("data/leagues/all/schedules.json", "w") as f:
    json.dump(filtered_schedule, f, indent=4)

print("Successfully removed all practice times from schedules.json")
