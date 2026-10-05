import os
from datetime import datetime, timezone, timedelta

import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

from database import (
    initialize_database,
    add_update_channel,
    remove_update_channel,
    is_update_channel,
    record_update,
    get_users,
    mark_reminded,
    get_update_channels,
)


# -------------------------
# Configuration
# -------------------------

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

# For testing, you can temporarily use 0.01
# 0.01 days = about 14.4 minutes
#
# For the real bot, change this back to 7.
DAYS_UNTIL_REMINDER = 1

# Your Discord server ID
GUILD_ID = 1496552936053149848
GUILD = discord.Object(id=GUILD_ID)


# -------------------------
# Discord setup
# -------------------------

intents = discord.Intents.default()

# We need this so the bot can see messages.
intents.message_content = True

class MyClient(discord.Client):

    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):

        self.tree.copy_global_to(guild=GUILD)

        await self.tree.sync(guild=GUILD)

        print("Commands synced to server:")
        for command in self.tree.get_commands(guild=GUILD):
            print(f"  /{command.name}")


bot = MyClient()
tree = bot.tree


# -------------------------
# Bot startup
# -------------------------

@bot.event
async def setup_hook():

    # Copy the commands defined in the tree
    # into this specific server.
    tree.copy_global_to(guild=GUILD)

    # Register those commands with Discord.
    await tree.sync(guild=GUILD)

    print("Commands synced to server:")
    for command in tree.get_commands(guild=GUILD):
        print(f"  /{command.name}")

@bot.event
async def on_ready():

    initialize_database()

    if not check_for_reminders.is_running():
        check_for_reminders.start()

    print(f"Logged in as {bot.user}")
    print("Bot is ready!")

# -------------------------
# Message tracking
# -------------------------

@bot.event
async def on_message(message):

    # Ignore messages from bots
    if message.author.bot:
        return

    # Ignore channels that aren't registered
    if not is_update_channel(message.channel.id):
        return

    # Record this user's update.
    #
    # This also clears their previous reminder timestamp,
    # so the reminder cycle starts over.
    record_update(message.author.id)

    print(
        f"Update recorded: "
        f"{message.author} in #{message.channel.name}"
    )


# -------------------------
# Add an update channel
# -------------------------

@tree.command(
    name="add-updates-channel",
    description="Make a channel count as an updates channel."
)
@app_commands.describe(
    channel="The channel that should count as an updates channel."
)
async def add_updates_channel(
    interaction: discord.Interaction,
    channel: str
):

    print("CHANNEL RECEIVED:")
    print("ID:", channel.id)
    print("NAME:", channel.name)
    print("TYPE:", type(channel))

    add_update_channel(
        channel.id,
        channel.name
    )

    await interaction.response.send_message(
        f"✅ {channel.mention} is now an updates channel.",
        ephemeral=True
    )


# -------------------------
# Remove an update channel
# -------------------------

@tree.command(
    name="remove-updates-channel",
    description="Stop a channel from counting as an updates channel."
)
@app_commands.describe(
    channel="The channel to remove."
)
async def remove_updates_channel(
    interaction: discord.Interaction,
    channel: str
):

    remove_update_channel(channel.id)

    await interaction.response.send_message(
        f"✅ {channel.mention} is no longer an updates channel.",
        ephemeral=True
    )


# -------------------------
# Show registered channels
# -------------------------

@tree.command(
    name="updates-channels",
    description="Show which channels are being monitored."
)
async def updates_channels(
    interaction: discord.Interaction
):

    channels = get_update_channels()

    if not channels:
        await interaction.response.send_message(
            "No updates channels have been registered.",
            ephemeral=True
        )
        return

    channel_mentions = []

    for channel_id, channel_name in channels:

        channel = interaction.guild.get_channel(channel_id)

        if channel:
            channel_mentions.append(channel.mention)
        else:
            channel_mentions.append(
                f"#{channel_name}"
            )

    await interaction.response.send_message(
        "**Monitored update channels:**\n"
        + "\n".join(channel_mentions),
        ephemeral=True
    )


# -------------------------
# Reminder checker
# -------------------------

@tasks.loop(hours=1)
async def check_for_reminders():

    now = datetime.now(timezone.utc)

    users = get_users()

    for user_id, last_update, last_reminder in users:

        last_update_time = datetime.fromisoformat(
            last_update
        )

        time_since_update = (
            now - last_update_time
        )

        # User has not reached the reminder threshold yet.
        if time_since_update < timedelta(
            days=DAYS_UNTIL_REMINDER
        ):
            continue

        # If we've already reminded them, only send
        # another reminder once another DAYS_UNTIL_REMINDER
        # period has passed.
        #
        # With DAYS_UNTIL_REMINDER = 1:
        #     first reminder -> after 1 day
        #     second reminder -> 1 day later
        #     third reminder -> 1 day later
        #     etc.
        #
        # With the real setting of 7, this would instead
        # remind every 7 days, which is NOT what you want.
        #
        # Therefore we handle the first reminder separately below.

        if last_reminder is not None:

            last_reminder_time = datetime.fromisoformat(
                last_reminder
            )

            time_since_reminder = (
                now - last_reminder_time
            )

            if time_since_reminder < timedelta(days=1):
                continue

        # Try to DM the user
        try:

            user = await bot.fetch_user(user_id)

            await user.send(
                "🔔 **Update Reminder**\n\n"
                "It's been 7 days since your last "
                "message in an updates channel.\n\n"
                "Please send an update when you get a chance!"
            )

            mark_reminded(user_id)

            print(
                f"Reminder sent to {user}"
            )

        except discord.Forbidden:

            print(
                f"Could not DM user {user_id}. "
                "Their DMs may be disabled."
            )

        except discord.HTTPException as error:

            print(
                f"Discord error while DMing "
                f"{user_id}: {error}"
            )


# -------------------------
# Start the bot
# -------------------------

bot.run(TOKEN)
