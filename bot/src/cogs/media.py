import random
import discord
from discord.ext import commands
import requests
import googleapiclient.discovery
from dotenv import load_dotenv
import os

load_dotenv()


class Media(commands.Cog):
    def __init__(self, bot):
        """
        Initializes the Media cog with the bot instance and API keys.

        Parameters:
        - bot (commands.Bot): The bot instance to associate with this cog.
        """
        self.bot = bot
        self.cx = os.getenv("CX")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")

    # ======== Data Processing ========

    async def fetch_search_results(self, search_url, search_params):
        """
        Fetches search results from an API based on the provided URL and parameters.

        Parameters:
        - search_url (str): The URL for the API request.
        - search_params (dict): The parameters to send with the API request.

        Returns:
        - list: A list of URLs of the search results.
        """
        response = requests.get(search_url, params=search_params).json()
        return [item["link"] for item in response.get("items", [])]

    async def create_embed(self, ctx, query, result_type, results, number, footer_text):
        """
        Creates and sends an embedded message with search results.

        Parameters:
        - ctx (commands.Context): The context in which the command was invoked.
        - query (str): The search query.
        - result_type (str): The type of result (e.g., "image", "GIF").
        - results (list): The list of search result URLs.
        - number (str): The selected result number.
        - footer_text (str): Text to display in the footer of the embed.

        Description:
        Sends either a random or a specific search result as an embed message. If no results are found, a message is sent indicating no results.
        """
        if not results:
            await ctx.reply(f"No {result_type} found.")
        elif number == "-1":
            embeds = []
            for result_url in results:
                embed = discord.Embed(
                    title=f"Here's a {query} {result_type} for you!",
                    color=discord.Color.blurple(),
                )
                embed.set_image(url=result_url)
                embed.set_footer(
                    text=f"{results.index(result_url) + 1} of {len(results)} {footer_text}"
                )
                embeds.append(embed)
                await ctx.reply(result_type)
            await ctx.reply(embeds=embeds)
        else:
            result_url = results[int(number) - 1]
            embed = discord.Embed(
                title=f"Here's a {query} {result_type} for you!",
                color=discord.Color.blurple(),
            )
            embed.set_image(url=result_url)
            embed.set_footer(
                text=f"{results.index(result_url) + 1} of {len(results)} {footer_text}"
            )
            await ctx.reply(embed=embed)

    async def google_image_search(self, ctx, query, number, result_type, img_type=None):
        """
        Performs a Google image search with optional image type filter.

        Parameters:
        - ctx (commands.Context): The context in which the command was invoked.
        - query (str): The search query for the image.
        - number (str): The selected result number.
        - result_type (str): The type of result (e.g., "image", "GIF").
        - img_type (str, optional): The type of image (e.g., "animated" for GIFs). Defaults to None.

        Description:
        Performs a Google image search and returns results based on the query, number, and optional image type.
        """
        search_params = {
            "q": query,
            "searchType": "image",
            "cx": self.cx,
            "key": self.google_api_key,
            "num": 10,
        }
        if img_type:
            search_params["imgType"] = img_type

        results = await self.fetch_search_results(
            "https://www.googleapis.com/customsearch/v1", search_params
        )
        await self.create_embed(ctx, query, result_type, results, number, "")

    async def youtube_video_search(self, ctx, query):
        """
        Performs a YouTube video search and sends an embed with a random video result.

        Parameters:
        - ctx (commands.Context): The context in which the command was invoked.
        - query (str): The search query for the video.

        Description:
        Searches for YouTube videos based on the query and returns a random video in the form of an embedded message.
        """
        search_params = {
            "q": query,
            "type": "video",
            "part": "id",
            "maxResults": 50,
        }
        youtube = googleapiclient.discovery.build(
            "youtube", "v3", developerKey=self.google_api_key
        )
        results = youtube.search().list(**search_params).execute()
        videos = [
            item["id"]["videoId"]
            for item in results["items"]
            if item["id"]["kind"] == "youtube#video"
        ]

        if not videos:
            await ctx.reply("No videos found.")
        else:
            video_id = random.choice(videos)
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            embed = discord.Embed(
                title=f"Here's a {query} video for you!",
                color=discord.Color.blurple(),
            )
            embed.add_field(name="Video URL", value=video_url, inline=False)
            embed.set_image(url=f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg")
            embed.set_footer(
                text=f"{videos.index(video_id) + 1} of {len(videos)} videos"
            )
            await ctx.reply(embed=embed)

    async def image_search_helper(self, ctx, query: str, is_gif: bool):
        """
        Handles search queries and determines whether to search for images or GIFs based on the query.

        Parameters:
        - ctx (commands.Context): The context in which the command was invoked.
        - query (str): The search query to be used.
        - is_gif (bool): A flag indicating whether to search for GIFs (True) or images (False).

        Description:
        Processes the search query and performs either an image or GIF search, based on the user's request.
        Handles optional result selection and ensures a valid number is used.
        """
        parts = query.split(" ")
        if len(parts) == 0:
            await ctx.reply("Nothing to search for.")
            print("Query missing in `Media.image_search_helper`")
            return

        last_part = parts[-1]
        number = random.randint(1, 10)
        if last_part == "-1" or last_part.isdigit():
            number = int(last_part)
            query = " ".join(parts[:-1])
        else:
            query = " ".join(parts)

        if number > 10 or number == 0:
            number = random.randint(1, 10)

        if not is_gif:
            if number < 0:
                for n in range(1, 11):
                    await self.google_image_search(ctx, query, n, "image")
            else:
                await self.google_image_search(ctx, query, number, "image")
        else:
            if number < 0:
                for n in range(1, 11):
                    await self.google_image_search(
                        ctx, query, n, "GIF", img_type="animated"
                    )
            else:
                await self.google_image_search(
                    ctx, query, number, "GIF", img_type="animated"
                )

    # ======== Commands ========

    @commands.command(
        name="image", help="Searches for an image based on the provided query."
    )
    async def image_command(self, ctx, *, query: str):
        """
        **Usage:** `.image <query> <selection>`

        **Parameters:**
        - `<query>` - The query used to find an image.
        - `<selection>` (optional) - A number (1-10) to chose a specific result out of the found images.

        **Example:**
        - `.image dog walking in park` → "Returns a random image of a dog walking in the park."
        - `.image cat playing piano 4` → "Returns the 4th found image of a cat playing the piano."

        **Description:**
        Finds a specific image based on the provided query and result selection. If no result selection is provided, a random selection out of the found results will be returned.
        """
        await self.image_search_helper(ctx, query, False)

    @commands.command(
        name="gif", help="Searches for a GIF based on the provided query."
    )
    async def gif_command(self, ctx, *, query: str):
        """
        **Usage:** `.gif <query> <selection>`

        **Parameters:**
        - `<query>` - The query used to find a GIF.
        - `<selection>` (optional) - A number (1-10) to chose a specific result out of the found GIFs.

        **Example:**
        - `.gif dog walking in park` → "Returns a random GIF of a dog walking in the park."
        - `.gif cat playing piano 4` → "Returns the 4th found GIF of a cat playing the piano."

        **Description:**
        Finds a specific GIF based on the provided query and result selection. If no result selection is provided, a random selection out of the found results will be returned.
        """
        await self.image_search_helper(ctx, query, True)

    @commands.command(
        name="video", help="Searches for a YouTube video based on the provided query."
    )
    async def video_command(self, ctx, *, query):
        """
        **Usage:** `.video <query> <selection>`

        **Parameters:**
        - `<query>` - The query used to find an video.
        - `<selection>` (optional) - A number (1-10) to chose a specific result out of the found videos.

        **Example:**
        - `.video dog walking in park` → "Returns a random video of a dog walking in the park."
        - `.video cat playing piano 4` → "Returns the 4th found video of a cat playing the piano."

        **Description:**
        Finds a specific video based on the provided query and result selection. If no result selection is provided, a random selection out of the found results will be returned.
        """
        await self.youtube_video_search(ctx, query)


async def setup(bot):
    """
    Sets up the Media cog by adding it to the bot client.

    Parameters:
    - bot (commands.Bot): The bot instance to add the cog to.
    """
    await bot.add_cog(Media(bot))
