import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def connect_railway():
    # Try different environment variables for Railway connection
    url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL")

    if not url:
        print(
            "❌ No Railway database URL found. Check DATABASE_PUBLIC_URL or DATABASE_URL environment variables."
        )
        return None

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    import urllib.parse as urlparse

    parsed = urlparse.urlparse(url)

    return psycopg2.connect(
        dbname=parsed.path[1:],
        user=parsed.username,
        password=parsed.password,
        host=parsed.hostname,
        port=parsed.port or 5432,
        sslmode="require",
    )


def check_schema():
    conn = connect_railway()
    if not conn:
        return

    cur = conn.cursor()

    print("=== RAILWAY DATABASE DATA CHECK ===")

    # Check if key tables have data
    key_tables = [
        "users",
        "players",
        "match_scores",
        "schedule",
        "series_stats",
        "series_leagues",
        "leagues",
        "clubs",
        "series",
    ]
    print(f"\n📊 DATA COUNTS:")
    total_records = 0

    for table in key_tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            total_records += count
            status = "✅" if count > 0 else "❌"
            print(f"  {status} {table}: {count:,} rows")
        except Exception as e:
            print(f"  ⚠️  {table}: Error - {e}")

    print(f"\n📈 TOTAL RECORDS: {total_records:,}")

    if total_records == 0:
        print("\n🚨 CRITICAL ISSUE: Railway database has NO DATA!")
        print("   This explains why the application shows no data.")
        print("   The schema is correct but data is missing.")
    else:
        print(f"\n✅ Railway database has data - investigating other issues needed")

    cur.close()
    conn.close()


if __name__ == "__main__":
    check_schema()
