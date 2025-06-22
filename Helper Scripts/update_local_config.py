#!/usr/bin/env python3
import glob
import os


def update_local_config():
    """Update local configuration files with new database URL"""

    old_url = "postgresql://postgres:OoxuYNiTfyRqbqyoFTNTUHRGjtjHVscf@trolley.proxy.rlwy.net:34555/railway"
    new_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

    print("🔧 Updating local configuration files")
    print("=" * 50)

    # Files to search and update
    files_to_check = [
        "test_railway_connection.py",
        "sync_railway_schema.py",
        "alembic/env.py",
        "overwrite_prod_db.sh",
        "scripts/test_railway_connection.py",
        "scripts/sync_data.py",
    ]

    updated_files = []

    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"\n📄 Checking {file_path}...")

            # Read file content
            with open(file_path, "r") as f:
                content = f.read()

            # Check if old URL exists
            if old_url in content:
                print(f"  🔄 Found old URL, updating...")

                # Replace old URL with new URL
                new_content = content.replace(old_url, new_url)

                # Write updated content back
                with open(file_path, "w") as f:
                    f.write(new_content)

                print(f"  ✅ Updated {file_path}")
                updated_files.append(file_path)
            else:
                print(f"  ℹ️  No old URL found in {file_path}")

    # Also update any hardcoded host/port references
    host_port_files = ["overwrite_prod_db.sh"]

    for file_path in host_port_files:
        if os.path.exists(file_path):
            print(f"\n📄 Checking {file_path} for host/port references...")

            with open(file_path, "r") as f:
                content = f.read()

            # Replace old host and port
            if "trolley.proxy.rlwy.net" in content and "34555" in content:
                print(f"  🔄 Updating host and port...")

                new_content = content.replace(
                    "trolley.proxy.rlwy.net", "ballast.proxy.rlwy.net"
                )
                new_content = new_content.replace("34555", "40911")
                new_content = new_content.replace(
                    "OoxuYNiTfyRqbqyoFTNTUHRGjtjHVscf",
                    "HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq",
                )

                with open(file_path, "w") as f:
                    f.write(new_content)

                print(f"  ✅ Updated {file_path}")
                updated_files.append(file_path)

    print(f"\n📊 Summary:")
    print(f"✅ Updated {len(updated_files)} files:")
    for file_path in updated_files:
        print(f"  - {file_path}")

    if len(updated_files) == 0:
        print("ℹ️  No files needed updating (they may already be correct)")

    print(f"\n🎉 Local configuration update completed!")

    return updated_files


if __name__ == "__main__":
    update_local_config()
