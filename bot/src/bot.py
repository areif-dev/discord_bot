import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio


librespot = None 
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix=".", help_command=None, intents=intents)

# Dictionary to track disconnect tasks per guild
disconnect_tasks = {}

load_dotenv()


@bot.event
async def on_ready():
    """
    Event triggered when the bot has successfully connected to Discord and is ready to operate.

    This event sends a message to a specific channel to notify that the bot is online.
    It also loads all the cogs from the "cogs" directory, except the "__init__.py" file.
    """

    print(f"Logged in as {bot.user.name}")

    channel = bot.get_channel(int(os.getenv("CHANNEL_ID")))

    if channel:
        await channel.send(f"{bot.user.name} is online!")
    else:
        print(f"Could not find channel with provided ID")

    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            await bot.load_extension(f"cogs.{filename[:-3]}")


@bot.event
async def on_voice_state_update(member, before, after):
    """
    Listens to changes in voice channel state to automatically disconnect the bot when it is 
    alone for 5 minutes. Also listens for members rejoining to prevent the bot from leaving 
    if someone just joined.

    :param member: Information about the member whose voice state has changed 
    :param before: The state of the voice client before the change. Not used here
    :param after: The state of the voice client after the change. Not used here
    """

    # Don't do anything if the the bot's state has changed or if the member is not in a voice channel
    if member.bot or not member.guild.voice_client:
        return

    channel = member.guild.voice_client.channel

    # If the bot is in a channel, check if it's alone 
    if len(channel.members) == 1 and channel.members[0] == bot.user:
        # Start disconnect timer if not already running
        if member.guild.id not in disconnect_tasks:
            print("Starting disconnect task")
            task = asyncio.create_task(disconnect_after_timeout(member.guild.voice_client, member.guild.id))
            disconnect_tasks[member.guild.id] = task
    else:
        # Cancel any pending disconnects if people joined back
        if member.guild.id in disconnect_tasks:
            print("Stopping disconnect task")
            disconnect_tasks[member.guild.id].cancel()
            del disconnect_tasks[member.guild.id]


async def disconnect_after_timeout(voice_client, guild_id):
    """
    Used by `on_voice_state_update`. Performs the action of disconnecting the bot after 5 minutes. 
    """

    try:
        await asyncio.sleep(300)  # 5 minutes
        if voice_client.is_connected():
            await voice_client.disconnect()
    except asyncio.CancelledError:
        # Task was canceled because someone rejoined
        pass
    finally:
        # Clean up
        if guild_id in disconnect_tasks:
            del disconnect_tasks[guild_id]


bot.run(os.getenv("DISCORD_BOT_TOKEN"))
