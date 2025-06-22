from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

# 🔁 Mapping of IDs to actual names (partial examples — update as needed!)
location_lookup = {
    "16161": "Wilmette PD",
    "16162": "Sunset Ridge",
    "16163": "Winnetka",
    "16164": "Exmoor",
    "16165": "Hinsdale PC",
    "16166": "Onwentsia",
    "16167": "Salt Creek",
    "16168": "Lakeshore S&amp;F",
    "16169": "Glen View",
    "16170": "Prairie Club",
    "16171": "Lake Forest",
    "16172": "Evanston ",
    "16173": "Midt-Bannockburn",
    "16174": "Briarwood",
    "16175": "Birchwood",
    "16176": "Hinsdale GC",
    "16177": "Butterfield",
    "16178": "Chicago Highlands",
    "16179": "Glen Ellyn",
    "16180": "Skokie",
    "16181": "Winter Club",
    "16182": "Westmoreland",
    "16183": "Valley Lo",
    "16184": "Tennaqua",
    "16185": "South Barrington",
    "16186": "Saddle &amp; Cycle",
    "16187": "Ruth Lake",
    "16188": "Northmoor",
    "16189": "North Shore",
    "16190": "Midtown - Chicago",
    "16191": "Michigan Shores",
    "16192": "Lake Shore CC",
    "16193": "Knollwood",
    "16194": "Indian Hill",
    "16195": "Glenbrook RC",
    "16196": "Hawthorn Woods",
    "16197": "Lake Bluff",
    "16198": "Barrington Hills CC",
    "16199": "River Forest PD",
    "16200": "Edgewood Valley",
    "16201": "Park Ridge CC",
    "16202": "Medinah",
    "16203": "LaGrange CC",
    "16204": "Dunham Woods",
    "16432": "BYE",
    "17241": "Lifesport-Lshire",
    "17242": "Biltmore CC",
    "18332": "Bryn Mawr",
    "18333": "Glen Oak ",
    "18334": "Inverness ",
    "18335": "White Eagle",
    "18364": "Legends ",
    "19205": "River Forest CC",
    "19312": "Oak Park CC",
    "22561": "Royal Melbourne",
}

division_lookup = {
    "19022": "Chicago Legends",
    "19029": "Chicago 2",
    "19030": "Chicago 3",
    "19031": "Chicago 4",
    "19032": "Chicago 5",
    "19033": "Chicago 7",
    "19034": "Chicago 8",
    "19035": "Chicago 9",
    "19036": "Chicago 10",
    "19037": "Chicago 11",
    "19038": "Chicago 12",
    "19039": "Chicago 13",
    "19040": "Chicago 14",
    "19041": "Chicago 15",
    "19042": "Chicago 16",
    "19043": "Chicago 17",
    "19044": "Chicago 18",
    "19045": "Chicago 19",
    "19046": "Chicago 20",
    "19047": "Chicago 21",
    "19048": "Chicago 22",
    "19049": "Chicago 23",
    "19050": "Chicago 24",
    "19051": "Chicago 25",
    "19052": "Chicago 26",
    "19053": "Chicago 27",
    "19054": "Chicago 28",
    "19055": "Chicago 29",
    "19056": "Chicago 30",
    "19066": "Chicago 6",
    "19068": "Chicago 25 SW",
    "19069": "Chicago 15 SW",
    "19070": "Chicago 17 SW",
    "19071": "Chicago 21 SW",
    "19072": "Chicago 11 SW",
    "19073": "Chicago 19 SW",
    "19076": "Chicago 9 SW",
    "19078": "Chicago 31",
    "19556": "Chicago 7 SW",
    "19558": "Chicago 23 SW",
    "19559": "Chicago 13 SW",
    "19560": "Chicago 32",
    "26722": "Chicago 34",
    "26829": "Chicago 99",
    "27694": "Chicago 27 SW",
    "28855": "Chicago 1",
    "28862": "Chicago 29 SW",
    "28865": "Chicago 33",
    "28867": "Chicago 35",
    "28868": "Chicago 36",
    "28869": "Chicago 37",
    "28870": "Chicago 38",
    "28871": "Chicago 39",
}

# 🌐 Step 1: Scrape the Ratings Table
url = "https://aptachicago.tenniscores.com/?mod=nndz-SkhmOW1PQ3V4Zz09"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")
table = soup.find("table")
df = pd.read_html(str(table))[0]

# 🕵️ Step 2: Extract Club and Series from class attributes
table_rows = table.find_all("tr")[1:]  # Skip header row
club_ids = []
division_ids = []

for row in table_rows:
    class_list = row.get("class", [])
    club_id = None
    division_id = None

    for cls in class_list:
        if cls.startswith("loc_"):
            club_id = cls.replace("loc_", "")
        if cls.startswith("diver_"):
            division_id = cls.replace("diver_", "")

    club_ids.append(location_lookup.get(club_id, "Unknown"))
    division_ids.append(division_lookup.get(division_id, "Unknown"))

# 🧩 Step 3: Add new columns to dataframe
df["Club"] = club_ids
df["Series"] = division_ids
df["Scraped_At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 🧼 Step 4: Clean and save locally
df = df.fillna("")
df = df.sort_values(by=["Last Name", "First Name"], ascending=[True, True])

# Save to CSV file with timestamp
current_date = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"player_ratings_{current_date}.csv"
df.to_csv(filename, index=False)

# Print summary to terminal
print("\n📊 Player Ratings Summary:")
print("-" * 80)
print(f"Total Players: {len(df)}")
print(f"Unique Clubs: {df['Club'].nunique()}")
print(f"Unique Series: {df['Series'].nunique()}")
print(f"\n✅ Data saved to {filename}")
print("-" * 80)

# Print detailed player list
print("\n👥 Player List:")
print("-" * 80)
for _, row in df.iterrows():
    print(f"{row['Last Name']}, {row['First Name']} | {row['Club']} | {row['Series']}")
print("-" * 80)
