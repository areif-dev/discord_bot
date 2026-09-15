import discord
from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot):
        """
        Initializes the General cog with the bot instance.

        Parameters:
        - bot (commands.Bot): The bot instance to associate with this cog.
        """
        self.bot = bot

    # ======== Listeners ========

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        Listens for errors raised during command execution and handles specific errors.

        Parameters:
        - ctx (commands.Context): The context of the command that caused the error.
        - error (Exception): The exception raised during the command execution.

        Handles the following errors:
        - CommandNotFound: Indicates that the command does not exist.
        - MissingRequiredArgument: Indicates that a required argument is missing.
        - BadArgument: Indicates that one of the arguments is invalid.
        - CheckFailure: Indicates that the user does not have permission to run the command.
        - Other errors: All other errors will trigger a general error message.
        """
        if isinstance(error, commands.CommandNotFound):
            await ctx.reply("That command was not found.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("You are missing a required argument.")
        elif isinstance(error, commands.BadArgument):
            await ctx.reply("There was an issue with one of your arguments.")
        elif isinstance(error, commands.CheckFailure):
            await ctx.reply("You do not have permission to run this command.")
        else:
            await ctx.reply("An error occurred. Please try again later.")
            raise error

    # ======== Commands ========

    @commands.command(name="ping", help="Responds with the bot's latency.")
    async def ping_command(self, ctx):
        """
        **Usage:** `.ping`

        **Description:**
        Returns the current latency that the bot is experiencing.
        """
        await ctx.reply(f"Pong! Latency: {round(self.bot.latency * 1000)}ms.")

    @commands.command(
        name="help",
        help="Shows a list of commands grouped by category, or detailed info if a specific command is provided.",
    )
    async def help_command(self, ctx, command_name: str = None):
        """
        **Usage:** `.help <command>`

        **Parameters:**
        - `<command>` (optional) - The name of a command.

        **Example:**
        - `.help ping` → "Returns an in-depth description of the '.ping' command and how to use it."
        - `.help` → "Returns a help message containing simple descriptions of all commands."

        **Description:**
        Returns a list of basic descriptions for all commands, or an in-depth description of one command if the name is provided.
        """
        if command_name:
            command = self.bot.get_command(command_name)

            if command:
                detailed_help = command.callback.__doc__
                if not detailed_help:
                    detailed_help = "No additional information available."

                embed = discord.Embed(
                    title=f"Help for `{command_name}`",
                    description=detailed_help.strip(),
                    color=discord.Color.blurple(),
                )
                await ctx.reply(embed=embed)
            else:
                await ctx.reply(f"Command `{command_name}` not found.")

        else:
            embed = discord.Embed(
                title="Available Commands",
                description="Use `.help <command>` for more details on a specific command.",
                color=discord.Color.blurple(),
            )

            for cog_name, cog in self.bot.cogs.items():
                command_list = [
                    f"`{cmd.name}` - {cmd.help or 'No description available.'}"
                    for cmd in cog.get_commands()
                    if not cmd.hidden
                ]

                if command_list:
                    embed.add_field(
                        name=f"**{cog_name}**",
                        value="\n".join(command_list),
                        inline=False,
                    )

            uncategorized = [
                f"`{cmd.name}` - {cmd.help or 'No description available.'}"
                for cmd in self.bot.commands
                if cmd.cog is None and not cmd.hidden
            ]

            if uncategorized:
                embed.add_field(
                    name="**Uncategorized**",
                    value="\n".join(uncategorized),
                    inline=False,
                )

            await ctx.reply(embed=embed)


async def setup(bot):
    """
    Sets up the General cog by adding it to the bot client.

    Parameters:
    - bot (commands.Bot): The bot instance to add the cog to.
    """
    await bot.add_cog(General(bot))
