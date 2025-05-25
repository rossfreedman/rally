#!/usr/bin/env python3
"""
YouTube Video Replacement Execution Guide
Provides clear options for executing the YouTube API replacement approach.
"""

import os
import sys
import subprocess

def show_current_status():
    """Show current status of the system."""
    print("📊 CURRENT STATUS")
    print("=" * 30)
    
    # Check JSON file
    json_file = 'data/complete_platform_tennis_training_guide.json'
    if os.path.exists(json_file):
        print("✅ JSON file: Found")
        try:
            import json
            with open(json_file, 'r') as f:
                data = json.load(f)
            print(f"📋 Techniques: {len(data)}")
            
            # Count videos
            total_videos = sum(len(tech.get('Reference Videos', [])) for tech in data.values())
            techniques_with_videos = sum(1 for tech in data.values() if tech.get('Reference Videos'))
            print(f"📹 Current videos: {total_videos} across {techniques_with_videos} techniques")
        except Exception as e:
            print(f"⚠️  JSON parsing error: {e}")
    else:
        print("❌ JSON file: Missing")
    
    # Check API key
    api_key = os.getenv('YOUTUBE_API_KEY')
    if api_key:
        print(f"🔑 API key: Configured ({api_key[:10]}...)")
    else:
        print("🔑 API key: Not configured")
    
    # Check dependencies
    try:
        import googleapiclient
        print("📦 Dependencies: Installed")
    except ImportError:
        print("📦 Dependencies: Missing")

def show_options():
    """Show execution options."""
    print("\n🎯 EXECUTION OPTIONS")
    print("=" * 30)
    print("1. 🚀 Guided Setup (Recommended)")
    print("   - Checks dependencies")
    print("   - Helps set up API key")
    print("   - Runs replacement process")
    print("   Command: python setup_youtube_replacement.py")
    
    print("\n2. ⚡ Direct Replacement")
    print("   - Runs replacement immediately")
    print("   - Uses existing API key or curated videos only")
    print("   Command: python replace_youtube_videos.py")
    
    print("\n3. 🧪 Test Setup First")
    print("   - Verifies everything is working")
    print("   - Shows current status")
    print("   Command: python test_replacement_setup.py")
    
    print("\n4. 📚 Read Documentation")
    print("   - Complete setup guide")
    print("   - Troubleshooting tips")
    print("   File: YOUTUBE_REPLACEMENT_README.md")

def get_api_key_instructions():
    """Show API key setup instructions."""
    print("\n🔑 API KEY SETUP")
    print("=" * 20)
    print("1. Go to: https://console.cloud.google.com/")
    print("2. Create/select a project")
    print("3. Enable YouTube Data API v3")
    print("4. Create an API key")
    print("5. Set environment variable:")
    print("   export YOUTUBE_API_KEY='your_key_here'")
    print("\nFor permanent setup:")
    print("   echo 'export YOUTUBE_API_KEY=\"your_key\"' >> ~/.zshrc")
    print("   source ~/.zshrc")

def run_option(choice):
    """Execute the chosen option."""
    if choice == "1":
        print("\n🚀 Running Guided Setup...")
        try:
            subprocess.run([sys.executable, 'setup_youtube_replacement.py'])
        except KeyboardInterrupt:
            print("\n⚠️  Setup cancelled by user")
        except Exception as e:
            print(f"\n❌ Error running setup: {e}")
    
    elif choice == "2":
        print("\n⚡ Running Direct Replacement...")
        try:
            subprocess.run([sys.executable, 'replace_youtube_videos.py'])
        except KeyboardInterrupt:
            print("\n⚠️  Replacement cancelled by user")
        except Exception as e:
            print(f"\n❌ Error running replacement: {e}")
    
    elif choice == "3":
        print("\n🧪 Running Test Setup...")
        try:
            subprocess.run([sys.executable, 'test_replacement_setup.py'])
        except Exception as e:
            print(f"\n❌ Error running test: {e}")
    
    elif choice == "4":
        print("\n📚 Opening documentation...")
        if os.path.exists('YOUTUBE_REPLACEMENT_README.md'):
            print("Documentation file: YOUTUBE_REPLACEMENT_README.md")
            print("Open this file in your editor to read the complete guide.")
        else:
            print("❌ Documentation file not found")
    
    elif choice.lower() == "api":
        get_api_key_instructions()
    
    else:
        print("❌ Invalid choice")

def main():
    """Main execution function."""
    print("🎾 YouTube Video Replacement - Execution Guide")
    print("=" * 60)
    
    show_current_status()
    show_options()
    
    print("\n" + "=" * 60)
    print("💡 RECOMMENDATIONS:")
    
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("• Set up YouTube API key for best results")
        print("• Or run with curated videos only (still improves many techniques)")
    else:
        print("• API key configured - ready for full replacement!")
    
    print("• Always review the generated report after replacement")
    print("• Backup is created automatically - you can always revert")
    
    print("\n" + "=" * 60)
    print("Choose an option (1-4) or 'api' for API setup help:")
    
    try:
        choice = input("Your choice: ").strip()
        if choice:
            run_option(choice)
        else:
            print("No option selected. Exiting.")
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main() 