import asyncio
from typing import Optional
import discord
import json
from discord.ext import commands
import os
import subprocess


class Sound:
    """
    Represents a sound that can be played in a Discord voice channel.

    :param name: The name of the sound.
    :param file: The file path of the sound.
    :param url: The source URL of the sound (if applicable).
    """

    def __init__(self, name: str, file: str, url: Optional[str]) -> None:
        self.name = name
        self.file = file
        self.url = url

    def to_json(self) -> dict[str, Optional[str]]:
        """
        Converts the Sound object into a JSON-serializable dictionary.

        :return: A dictionary representation of the sound.
        """

        return self.__dict__


class Soundboard(commands.Cog):
    """
    A Discord bot cog that manages sound effects for voice channels.

    :param client: The Discord bot client instance.
    """

    def __init__(self, bot):
        self.bot = bot  # Discord bot client
        self.sounds: dict[str, Sound] = self.init_sounds()

    def init_sounds(self) -> dict[str, Sound]:
        """
        Loads sound data from sounds.json.

        :return: A dictionary of sound names mapped to Sound objects.
        """

        try:
            with open("sounds.json", "r") as f:
                sound_data = json.load(f)
        except FileNotFoundError:
            with open("sounds.json", "w") as f:
                f.write("{}")
                sound_data = {}
        except json.JSONDecodeError:
            print("Error in Soundboard. Could not decode sounds.json")
            sound_data = {}

        sounds: dict[str, Sound] = {}
        for name, sound in sound_data.items():
            sounds[name] = Sound(name, sound["file"], sound["url"])
        return sounds

    def add_sound(self, sound: Sound):
        """
        Adds a new sound to the soundboard and updates the JSON file.

        :param sound: The sound object to be added.
        """

        self.sounds[sound.name] = sound
        with open("sounds.json", "w") as f:
            json.dump(self.to_json(), f)

    def remove_sound(self, name: str) -> Optional[Sound]:
        """
        Removes a sound from the soundboard and deletes the file.

        :param name: The name of the sound to remove.
        :return: The removed sound object if found, else None.
        """

        if name not in self.sounds:
            return None
        sound = self.sounds.pop(name)

        try:
            os.remove(sound.file)
        except FileNotFoundError:
            print(f"Failed to remove {sound.file} in `Soundboard.remove_sound`")

        with open("sounds.json", "w") as f:
            json.dump(self.to_json(), f)

        return sound

    def to_json(self) -> dict[str, Optional[str]]:
        """
        Converts the soundboard into a JSON-serializable dictionary.

        :return: A dictionary representation of the soundboard.
        """

        json = {}
        for name, sound in self.sounds.items():
            json[name] = sound.to_json()
        return json

    @commands.group(
        name="sound",
        invoke_without_command=True,
        help="Allows the user to interact with the integrated soundboard.",
    )
    async def sound(self, ctx):
        """
        **Usage:** `.sound <command>`

        **Parameters:**
        - `<command>` - The command to perform on the soundboard.

        **Example:**
        - `.sound add <url> <name>` → "Downloads a soundbyte from <url> and adds it to the soundboard under <name>."
        - `.sound rm` → "Display a sound menu to remove a sound."
        - `.sound pick` → "Display the soundboard to play a sound."

        **Description:**
        Allows the user to interact with the integrated soundboard.
        """
        await ctx.reply(
            "```\n"
            "add <url> <name>  Downloads a soundbyte from <url> and adds it to the soundboard under <name>\n"
            "rm                Display a sound menu to remove a sound\n"
            "pick              Display the soundboard to play a sound```"
        )

    @sound.command()
    async def add(self, ctx, url: str, name: str):
        """
        Downloads a soundbyte from <url> and adds it to the soundboard under <name>

        :param ctx: The command context
        :param url: The url of the sound to download
        :param name: What to call the soundbyte
        """

        if name in self.sounds:
            await ctx.reply(f"There is already a soundbyte called {name}")
            return

        try:
            if file_size(url) > 100_000_000:  # Prevent downloading large files
                await ctx.reply("Cannot download files over 100MB")
                return
        except Exception as e:
            await ctx.reply(
                f"Cannot verify the size of your download because of ```\n{e}```"
            )
            print(f"Cannot verify the size of your download because of ```\n{e}```")
            return

        os.makedirs("sounds", exist_ok=True)
        process = subprocess.run(
            f"python3 -m yt_dlp -x --format=bestaudio/best --embed-thumbnail --add-metadata -o sounds/{name} {url}".split(
                " "
            ),
            capture_output=True,
        )
        if process.returncode != 0:
            await ctx.reply(
                f"Failed to download sound because of ```\n{process.stderr.decode()}```"
            )
            print(
                f"Failed to download sound because of ```\n{process.stderr.decode()}```"
            )
            return
        try:
            file_path = extract_file_path(process.stdout)
        except Exception as e:
            await ctx.reply(f"Failed to get sound file path because of ```\n{e}```")
            print(f"Failed to get sound file path because of ```\n{e}```")
            return

        self.add_sound(Sound(name, file_path, url))
        await ctx.reply(f"Added soundbyte called {name} from {url}")

    @sound.command()
    async def rm(self, ctx):
        """
        Opens a menu to pick a sound to remove from the soundboard

        :param ctx: The context of the interaction
        """

        if not self.sounds or len(self.sounds) == 0:
            await ctx.reply("There are no sounds to be removed!")
            return
        view = SoundSelect(self, True, ctx)
        await ctx.reply("Pick a sound to remove:", view=view)

    @sound.command()
    async def pick(self, ctx):
        """
        Opens the sound selection menu.

        :param ctx: The command context.
        """

        if not self.sounds or len(self.sounds) == 0:
            await ctx.reply(
                "No sounds available! You can add some with ```\n.sound add <url> <name>```"
            )
            return

        view = SoundSelect(self, False, ctx)
        await ctx.reply("Pick a sound to play:", view=view)


class SoundSelect(discord.ui.View):
    """
    A Discord UI View that provides buttons for selecting and playing sounds.

    :param soundboard: The soundboard instance containing available sounds.
    :param remove: `True` if the selection will be used to remove a sound. `False` if the selection will play the sound
    :param ctx: The context of the command execution.
    """

    def __init__(self, soundboard: Soundboard, remove: bool, ctx):
        if remove:
            super().__init__(
                timeout=60
            )  # Set a timeout on the remove picker just in case
        else:
            super().__init__()
        self.soundboard = soundboard
        self.ctx = ctx

        for sound_name in self.soundboard.sounds.keys():
            if remove:
                self.add_item(RemoveSoundButton(sound_name, soundboard, ctx))
            else:
                self.add_item(PlaySoundButton(sound_name, soundboard, ctx))


class RemoveSoundButton(discord.ui.Button):
    """
    A button representing an individual sound, which is removed from the soundboard when clicked.

    :param sound_name: The name of the sound.
    :param soundboard: The soundboard instance containing the sound.
    :param ctx: The context of the command execution.
    """

    def __init__(self, sound_name: str, soundboard: Soundboard, ctx):
        super().__init__(label=sound_name, style=discord.ButtonStyle.danger)
        self.sound_name = sound_name
        self.soundboard = soundboard
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        """
        Handles the button click event and removes the selected sound.

        :param interaction: The Discord interaction object.
        """

        url = self.soundboard.sounds[self.sound_name].url
        self.soundboard.remove_sound(self.sound_name)
        await interaction.response.send_message(
            f'Removed sound "{self.sound_name}" with url {url}'
        )


class PlaySoundButton(discord.ui.Button):
    """
    A button representing an individual sound, which plays when clicked.

    :param sound_name: The name of the sound.
    :param soundboard: The soundboard instance containing the sound.
    :param ctx: The context of the command execution.
    """

    def __init__(self, sound_name, soundboard, ctx):
        super().__init__(label=sound_name, style=discord.ButtonStyle.primary)
        self.sound_name = sound_name
        self.soundboard = soundboard
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        """
        Handles the button click event and plays the selected sound.

        :param interaction: The Discord interaction object.
        """

        sound = self.soundboard.sounds[self.sound_name]
        voice_client = discord.utils.get(
            self.ctx.bot.voice_clients, guild=self.ctx.guild
        )

        if not voice_client or not voice_client.is_connected():
            if self.ctx.author.voice and self.ctx.author.voice.channel:
                voice_client = await self.ctx.author.voice.channel.connect()
            else:
                await interaction.response.send_message(
                    "You must be in a voice channel!", ephemeral=True
                )
                return

        if voice_client.is_playing():
            voice_client.stop()

        def after_playing(error):
            if error:
                print(f"Encountered error in `after_playing` for a soundbyte: {error}")
                return

            if voice_client.is_playing():
                print("Still playing audio in soundboard.")
                return

            coro = voice_client.disconnect()
            fut = asyncio.run_coroutine_threadsafe(coro, self.ctx.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error in after_playing: {e}")

        voice_client.play(
            discord.FFmpegPCMAudio(
                sound.file,
                options="-af loudnorm=I=-14:TP=-2:LRA=11",
            ),
            after=after_playing,
        )
        await interaction.response.defer()  # Some response is required to let the user know their interaction worked


def extract_file_path(ytdl_stdout: bytes) -> str:
    """
    Parses the standard output of a yt-dlp call to read the file path where a file
    was saved

    :param ytdl_stdout: The byte array passed from the stdout of a yt-dlp call
    :return: The file path extracted from stdout
    """

    last_line = ytdl_stdout.split(b"\n").pop(-2)  # The last line that is not blank
    path_start_index = (
        47  # The file path should start at the 46th index of the last line
    )
    path_end_index = (
        len(last_line) - 1
    )  # The file path should end at the second to last index of the last line
    return last_line[path_start_index:path_end_index].decode()


def file_size(url: str) -> int:
    """
    Get the size in bytes of the whole file at the given url

    :param url: The url to fetch the file size of
    :return: The size in bytes of the file at `url`
    """

    process = subprocess.run(
        f'python3 -m yt_dlp --format=bestaudio/best --print "%(filesize)d" {url}'.split(
            " "
        ),
        capture_output=True,
    )
    if process.returncode != 0:
        raise subprocess.CalledProcessError(
            process.returncode,
            "python3 -m yt_dlp",
            stderr=f"Cannot read file size of sound because of ```\n{process.stdout}```",
        )

    return int(process.stdout.decode().strip("\" \n'"))


async def setup(bot: commands.Bot):
    """
    Adds the Soundboard cog to the bot.

    :param client: The Discord bot client.
    """

    await bot.add_cog(Soundboard(bot))
