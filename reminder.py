# Github Actions daily job

import os
from datetime import datetime, timezone, timedelta

import discord
from dotenv import load_dotenv

from database import initialize_database, get_users, mark_reminded


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

DAYS_UNTIL_REMINDER = 7


intents = discord.Intents.default()

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    initialize_database()

    users = get_users()

    now = datetime.now(timezone.utc)
    reminder_threshold = now - timedelta(days=DAYS_UNTIL_REMINDER)

    for user_id, last_update, last_reminder in users:

        last_update_time = datetime.fromisoformat(last_update)

        # Make sure the timestamp is timezone-aware
        if last_update_time.tzinfo is None:
            last_update_time = last_update_time.replace(tzinfo=timezone.utc)

        # Skip users who have updated within the last 7 days
        if last_update_time > reminder_threshold:
            continue

        # Don't remind someone more than once
        # until they make another update
        if last_reminder is not None:
            print(f"Already reminded user {user_id}")
            continue

        try:
            user = await client.fetch_user(user_id)

            await user.send(
                "Hey! Just a reminder that you haven't posted an update "
                "in the last 7 days."
            )

            mark_reminded(user_id)

            print(f"Sent reminder to {user_id}")

        except Exception as e:
            print(f"Could not remind {user_id}: {e}")

    print("Reminder check complete.")

    await client.close()


client.run(TOKEN)