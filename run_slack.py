import sys
import os
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from app.config import settings
from slack.slack_app import slack_service

def main():
    print("=" * 65)
    print("🤖 SMART GROCERY AGENT - SLACK LIVE BOT")
    print("=" * 65)

    bot_token = settings.SLACK_BOT_TOKEN or os.getenv("SLACK_BOT_TOKEN")
    app_token = settings.SLACK_APP_TOKEN or os.getenv("SLACK_APP_TOKEN")

    if not bot_token or not bot_token.startswith("xoxb-"):
        print("\n❌ SLACK_BOT_TOKEN missing or invalid in .env!")
        print("Please set your Bot User OAuth Token in .env:")
        print("SLACK_BOT_TOKEN=xoxb-...\n")
        return

    if not app_token or not app_token.startswith("xapp-"):
        print("\n❌ SLACK_APP_TOKEN missing or invalid in .env!")
        print("Please set your App-Level Token (Socket Mode) in .env:")
        print("SLACK_APP_TOKEN=xapp-...\n")
        return

    print(f"✅ Bot Token: {bot_token[:10]}... detected")
    print(f"✅ App Token: {app_token[:10]}... detected")
    print(f"✅ Authorized Admin IDs: {settings.ADMIN_USER_IDS}")
    print("\nConnecting to Slack via Socket Mode...")

    slack_service.start_socket_mode()

if __name__ == "__main__":
    main()
