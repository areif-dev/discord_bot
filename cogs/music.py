import discord
from discord.ext import commands
import os
import urllib.parse
import urllib.parse
import spotify_controller
import time
from rapidfuzz import fuzz


class SearchModal(discord.ui.Modal, title="Song Search"):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.TextInput(label="Query", custom_id="query"))
        self.add_item(discord.ui.TextInput(label="Auto queue first match", default="Yes", custom_id="auto_queue", required=False))
        self.add_item(discord.ui.TextInput(label="Include results from", default="album,playlist,track,episode,audiobook", custom_id="type", required=False))

    @staticmethod
    def parse_toggler(raw_toggler_input: str) -> bool:
        try: 
            if raw_toggler_input.lower()[0] == "y":
                return True
            else: 
                return False
        except: 
            return False

    @staticmethod
    def fuzzyfind(query: str, pool: list[spotify_controller.Queueable]) -> spotify_controller.Queueable:
        query = query.lower()
        closest = None
        for item in pool:
            score = fuzz.ratio(query, item.search_str)
            if query == item.name: 
                score += 25
            elif item.name in query or query in item.name:
                score += 10

            if closest is None or score > closest[0]:
                closest = (score, item)

    async def on_submit(self, interaction: discord.Interaction):
        expected = "album,playlist,track,episode,audiobook"

        query = str(self.children[0])
        auto_queue = SearchModal.parse_toggler(str(self.children[1]))
        limit = 5
        if auto_queue:
            limit = 1

        raw_search_types = str(self.children[2])
        search_types = []
        for s in raw_search_types.split(","):
            s = s.strip()
            if s == "":
                continue
            if s not in expected.split(","):
                await interaction.response.send_message(f"Unexpected input for search type: `{s}`. Please enter a comma separated list of values containing only a combination of ```{expected}```")
                return 
            search_types.append(s)

        if len(search_types) == 0:
            search_types.append("track")

        raw_results = None
        try:
            raw_results = spotify_controller.search(query=query, limit=limit, search_type=search_types)
        except Exception as e:
            await interaction.response.send_message(f"Failed to execute search due to error: ```{e}```")
            return 

        search_results = []
        for search_t in search_types:
            search_results.append(spotify_controller.Queueable(raw_results[f"{search_t}s"]["items"]))

        if auto_queue:



class PlaybackView(discord.ui.View):
    """
    Buttons for controlling spotify playback, such as reverse, play/pause, and skip
    """

    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx 
        self.add_item(SkipBackButton(ctx))
        self.add_item(TogglePlayButton(ctx, ctx.guild.voice_client.is_playing()))
        self.add_item(SkipForwardButton(ctx))
        self.add_item(StopButton(ctx))
        self.add_item(SearchButton(ctx))


async def create_playback_embed(ctx) -> tuple[discord.Embed, PlaybackView]:
    """
    Constructs the message embed and view that constitute the playback menu 

    :param ctx: The current discord client context 
    :returns: Tuple. First member is the embed that displays the now playing and up next information.
    Second member is the view that contains buttons to control playback like revers, play/pause, 
    and skip
    """

    now_playing = spotify_controller.get_now_playing()
    queue = spotify_controller.get_queue()
    queue_str = "\n".join([f"- {track.discord_display_str()}" for track in queue[:4]])

    view = PlaybackView(ctx)
    embed = discord.Embed(title="Playback", color=discord.Color.blurple())
    embed.set_thumbnail(url=now_playing.image)
    embed.add_field(name="Now Playing", value=now_playing.discord_display_str(), inline=False)
    embed.add_field(name="Up Next", value=queue_str, inline=False)
    return (embed, view)


class SkipBackButton(discord.ui.Button):
    def __init__(self, ctx):
        super().__init__(emoji="⏪", style=discord.ButtonStyle.primary, custom_id="rewind")
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        voice_client = self.ctx.guild.voice_client
        if voice_client and voice_client.is_playing() and not voice_client.is_paused():
            spotify_controller.skip("previous")
            embed, view = await create_playback_embed(self.ctx)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(f"Nothing is playing right now")


class TogglePlayButton(discord.ui.Button):
    def __init__(self, ctx, is_playing: bool):
        emoji = "▶️"
        if is_playing:
            emoji = "⏸️"

        super().__init__(emoji=emoji, style=discord.ButtonStyle.primary, custom_id="toggle")
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        voice_client = self.ctx.guild.voice_client
        if not spotify_controller.is_playing() and voice_client and voice_client.is_paused():
            voice_client.resume()
            spotify_controller.play()
            
            embed, view = await create_playback_embed(self.ctx)
            await interaction.response.edit_message(embed=embed, view=view)

        elif spotify_controller.is_playing() and voice_client and voice_client.is_playing(): 
            spotify_controller.pause()
            voice_client.pause()
            embed, view = await create_playback_embed(self.ctx)
            await interaction.response.edit_message(embed=embed, view=view)

        else: 
            await interaction.response.send_message("No spotify steam found")


class SkipForwardButton(discord.ui.Button):
    def __init__(self, ctx):
        super().__init__(emoji="⏩", style=discord.ButtonStyle.primary, custom_id="next")
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        voice_client = self.ctx.guild.voice_client
        if voice_client and voice_client.is_playing() and not voice_client.is_paused():
            spotify_controller.skip("next")
            embed, view = await create_playback_embed(self.ctx)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(f"Nothing is playing right now")


class StopButton(discord.ui.Button):
    def __init__(self, ctx):
        super().__init__(emoji="⏹️", style=discord.ButtonStyle.primary, custom_id="stop")
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        voice_client = self.ctx.guild.voice_client
        if voice_client:
            if voice_client.is_playing():
                voice_client.stop()

            await voice_client.disconnect()
            spotify_controller.stop_librespot()
            await interaction.response.send_message(content="Disconnected")


class SearchButton(discord.ui.Button):
    def __init__(self, ctx):
        super().__init__(emoji="🔍", style=discord.ButtonStyle.primary, custom_id="search")
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        modal = SearchModal()
        await interaction.response.send_modal(modal)


class Music(commands.Cog):
    def __init__(self, bot):
        """
        Initializes the Music cog with the bot instance, song queue, and song history.

        Parameters:
        - bot (commands.Bot): The bot instance to which the cog will be added.
        """
        self.bot = bot

    # ======== Data Processing ========

    async def join_voice_channel(self, ctx):
        """
        Ensures the bot joins the same voice channel as the user who invoked the command.

        Parameters:
        - ctx (commands.Context): The context of the command invocation.
        """

        tokens = spotify_controller.get_access_token() 

        # We have an access token, but it has expired, so refresh it
        if tokens and "access_token" in tokens and tokens["access_token"] not in ("", None) and not spotify_controller.is_valid_token(tokens["access_token"]):
            # There is no refresh token either, so the user must relog
            if tokens["refresh_token"] in (None, ""):
                print(f"No valid access token or refresh token found")
                await ctx.reply("You are logged out. Try running `.login`")
                return 

            spotify_controller.refresh_token(tokens["refresh_token"])

        if spotify_controller.librespot is None:
            spotify_controller.start_librespot()
            wait_max = 10  # seconds
            wait = 0
            period = 1
            while spotify_controller.get_bot_device_id() is None and wait < wait_max:
                time.sleep(period)
                wait += period

            if spotify_controller.get_bot_device_id() is None: 
                print("Timeout attempting to start librespot.")
                await ctx.reply("Timeout attempting to start librespot. You may need to log in first: `.login`")
                return

        if ctx.author.voice and ctx.author.voice.channel:
            if ctx.guild.voice_client is None:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.guild.voice_client.move_to(ctx.author.voice.channel)
        else:
            await ctx.reply("You need to be in a voice channel to use this command.")

    async def add_to_queue(self, ctx, query):
        """
        Adds a song to the queue based on the search query.

        Parameters:
        - ctx (commands.Context): The context of the command invocation.
        - query (str): The song name or YouTube link to search for.
        """
        await self.join_voice_channel(ctx)
        search_results = spotify_controller.search(f'"{query}"')
        track_uri = search_results["tracks"]["items"][0]["uri"]
        print("adding to queue", spotify_controller.add_to_queue(track_uri))
        spotify_controller.switch_to_device()
        if not spotify_controller.is_playing():
            spotify_controller.play()

        # if self.currently_playing is not None:
        #     await self.send_now_playing(ctx, info)

    async def send_now_playing(self, ctx, info):
        """
        Sends an embedded message with the current song's details, including title, duration, and thumbnail.

        Parameters:
        - ctx (commands.Context): The context of the command invocation.
        - info (dict): Information about the song currently playing.
        """
        embed = discord.Embed(
            title=info["title"], url=info["webpage_url"], color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=info["thumbnail"])
        embed.add_field(
            name="Duration",
            value=humanize_duration(info["duration"]),
            inline=False,
        )
        await ctx.reply(embed=embed)

    async def play_next(self, ctx):
        """
        Plays the next song in the queue.
        If no songs remain, disconnects the bot from the voice channel.

        Parameters:
        - ctx (commands.Context): The context of the command invocation.
        """

        voice_client = ctx.guild.voice_client
        source = discord.FFmpegPCMAudio(
            pipe=True, 
            source=spotify_controller.librespot.stdout, 
            before_options="-f s16le -ar 44100 -ac 2",
            options="-f s16le -ar 48000 -ac 2",     
        )

        voice_client.play(source)
        # await self.send_now_playing(ctx, info)

    # ======== Commands ========

    @commands.command(name="playback", help="Display a menu for controlling music playback.")
    async def playback_command(self, ctx):
        await self.join_voice_channel(ctx)
        spotify_controller.switch_to_device()
        if not spotify_controller.is_playing():
            spotify_controller.play()
            
        voice_client = ctx.guild.voice_client 
        if voice_client and not voice_client.is_playing():
            source = discord.FFmpegPCMAudio(
                pipe=True, 
                source=spotify_controller.librespot.stdout, 
                before_options="-f s16le -ar 44100 -ac 2",
                options="-f s16le -ar 48000 -ac 2",     
            )
            voice_client.play(source)

        embed, view = await create_playback_embed(ctx)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="logout", help="Logout of the Current Account.")
    async def logout_command(self, ctx): 
        """
        **Usage:** `.logout`

        **Example:** 
        - `.logout` -> Removes all access tokens and requires a relog 

        **Description:**
        Removes all access tokens and requires a relog 
        """
        success = spotify_controller.logout()
        if success:
            await ctx.reply("Successfully logged out.")
        else:
            await ctx.reply("Looks like you're already logged out.")

        if ctx.guild.voice_client and ctx.guild.voice_client.is_connected():
            await ctx.guild.voice_client.disconnect()

        spotify_controller.stop_librespot()


    @commands.command(name="login", help="Login to a Spotify Premium account to play music.")
    async def login_command(self, ctx): 
        """
        **Usage:** `.login`

        **Example:** 
        - `.login` -> responds with a link to login to spotify 

        **Description:** 
        Shares a link to login to a Spotify Premium account 
        """
        search_params = {
            "scope": "streaming user-read-email user-read-private user-read-playback-state",
            "response_type": "code",
            "client_id": os.getenv("SPOTIFY_CLIENT_ID"),
            "redirect_uri": f"{os.getenv('AUTH_SERVER')}/callback",
            "state": os.getenv("AUTH_SERVER_SECURITY"),
        }
        query_string = urllib.parse.urlencode(search_params)
        url = f"https://accounts.spotify.com/authorize/?{query_string}"

        embed = discord.Embed(
            title="Spotify Premium Login", url=url, color=discord.Color.blurple()
        )

        await ctx.send(embed=embed)
        

    @commands.command(
        name="play", help="Adds a song to the queue and plays it if nothing is playing."
    )
    async def play_command(self, ctx, *, query):
        """
        **Usage:** `.play <query>`

        **Parameters:**
        - `<query>` - The name of (or link to) a YouTube video.

        **Example:**
        - `.play Never Gonna Give You Up` → "Joins the voice channel the user is in and begins playing Never Gonna Give You Up."

        **Description:**
        Adds a song to the queue and plays it if nothing is playing.
        """
        await self.add_to_queue(ctx, query)
        voice_client = ctx.guild.voice_client
        if voice_client and not voice_client.is_playing():
            await self.play_next(ctx)

    @commands.command(
name="stop", help="Stops the current song and clears the song queue."
    )
    async def stop_command(self, ctx):
        """
        **Usage:** `.stop`

        **Description:**
        Stops the current song and clears the song queue. Disconnects the bot from the voice channel if no song is playing.
        """

        voice_client = ctx.guild.voice_client
        if voice_client:
            if voice_client.is_playing():
                voice_client.stop()
                await voice_client.disconnect()
                return
            else:
                await voice_client.disconnect()
            await ctx.reply("Disconnecting.")
            spotify_controller.stop_librespot()

        await ctx.reply("I am not playing any songs right now.")

    @commands.command(
        name="skip", help="Skips the current song and plays the next one in the queue."
    )
    async def skip_command(self, ctx):
        """
        **Usage:** `.skip`

        **Description:**
        Skips the current song and plays the next one in the queue. If no songs remain, disconnects the bot from the voice channel.
        """
        voice_client = ctx.guild.voice_client
        if voice_client is not None:
            spotify_controller.skip("next")
            await ctx.reply("Skipping to the next song")
        else:
            await ctx.reply("I am not playing any songs right now.")

    @commands.command(
        name="back", help="Goes back to the previous song in history if available."
    )
    async def back_command(self, ctx):
        """
        **Usage:** `.back`

        **Description:**
        Goes back to the previous song in history if available. If no history exists, informs the user.
        """
        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_playing() and not voice_client.is_paused():
            spotify_controller.skip("previous")
            await ctx.reply("Returning to previous song")
        else:
            await ctx.reply("I am not playing any songs right now.")

    @commands.command(name="pause", help="Pauses the current song if it's playing.")
    async def pause_command(self, ctx):
        """
        **Usage:** `.pause`

        **Description:**
        Pauses the current song if it's playing. If no song is playing, informs the user.
        """
        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_playing() and not voice_client.is_paused():
            voice_client.pause()

        if spotify_controller.is_playing():
            spotify_controller.pause()
            await ctx.reply("Pausing playback")
        else:
            await ctx.reply("Already paused. You may have meant to use `.resume`")

    @commands.command(
        name="resume", help="Resumes the playback of the current song if it's paused."
    )
    async def resume_command(self, ctx):
        """
        **Usage:** `.resume`

        **Description:**
        Resumes the playback of the current song if it's paused. If no song is paused, informs the user.
        """
        if not spotify_controller.is_playing():
            voice_client = ctx.guild.voice_client
            if voice_client and voice_client.is_paused(): 
                voice_client.resume()

            spotify_controller.play()
            await ctx.reply("Resuming playback")
        else:
            await ctx.reply("Already playing. You may have meant to use `.pause`")

    @commands.command(name="rewind", help="Rewinds the current song to the start.")
    async def rewind_command(self, ctx):
        """
        **Usage:** `.rewind`

        **Description:**
        Rewinds the current song to the start and plays it again. If no song is playing, informs the user.
        """
        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_playing() and not voice_client.is_paused():
            voice_client.pause()
            self.song_queue.insert(0, self.currently_playing)
            await self.play_next(ctx)
        else:
            await ctx.reply("I am not playing any songs right now.")

    @commands.command(name="clear", help="Clears the song queue.")
    async def clear_queue_command(self, ctx):
        """
        **Usage:** `.clear`

        **Description:**
        Clears the song queue if there are any songs in the queue.
        """
        if len(self.song_queue) != 0:
            self.song_queue.clear()
            await ctx.reply("Cleared the queue.")
        else:
            await ctx.reply("Nothing in the queue to clear.")

    @commands.command(name="clearhistory", help="Clears the song history.")
    async def clear_history_command(self, ctx):
        """
        **Usage:** `.clearhistory`

        **Description:**
        Clears the song history if there are any songs in history.
        """
        if len(self.song_history) != 0:
            self.song_history.clear()
            await ctx.reply("Cleared the history.")
        else:
            await ctx.reply("Nothing in the history to clear.")

    @commands.command(
        name="queue", help="Displays the list of songs currently in the queue."
    )
    async def queue_command(self, ctx):
        """
        **Usage:** `.queue`

        **Description:**
        Displays the list of songs currently in the queue.
        """
        embed = discord.Embed(
            title="Song Queue",
            description="Here is the list of songs in the queue:",
            color=discord.Color.blurple(),
        )

        for index, song in enumerate(self.song_queue, start=1):
            embed.add_field(name=f"Song {index}", value=song["title"], inline=False)

        await ctx.send(embed=embed)

    @commands.command(
        name="history", help="Displays the list of previously played songs."
    )
    async def history_command(self, ctx):
        """
        **Usage:** `.history`

        **Description:**
        Displays the list of previously played songs.
        """
        embed = discord.Embed(
            title="Song History",
            description="Here is the list of previously played songs:",
            color=discord.Color.blurple(),
        )

        for index, song in enumerate(self.song_history, start=1):
            embed.add_field(name=f"Song {index}", value=song["title"], inline=False)

        await ctx.send(embed=embed)


async def setup(bot):
    """
    Sets up the Music cog by adding it to the bot client.

    Parameters:
    - bot (commands.Bot): The bot instance to which the cog will be added.
    """
    await bot.add_cog(Music(bot))
