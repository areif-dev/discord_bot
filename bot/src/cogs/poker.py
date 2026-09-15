import discord
from discord.ext import commands
import json
import os


class Poker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "poker_scores.json"
        self.scores = self.load_scores()

    def load_scores(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as f:
                return json.load(f)
        return {}

    def save_scores(self):
        with open(self.file_path, "w") as f:
            json.dump(self.scores, f, indent=4)

    def calculate_points(self, placement, num_players):
        total_points = 10 * num_players
        step = total_points / num_players
        points = total_points - (placement - 1) * step
        return round(points)

    @commands.command()
    async def add_results(self, ctx, *players: discord.Member):
        """Add results for a completed poker game. Max 10 players, ordered from 1st to last."""
        num_players = len(players)
        if num_players == 0 or num_players > 10:
            await ctx.reply(
                "Please provide between 1 and 10 players in order of placement (1st to last)."
            )
            return

        for i, player in enumerate(players):
            user_id = str(player.id)
            placement = i + 1  # 1-based placement
            points = self.calculate_points(placement, num_players)

            if user_id not in self.scores:
                self.scores[user_id] = {
                    "name": player.display_name,
                    "points": 0,
                    "games_played": 0,
                    "placement_sum": 0,
                }

            self.scores[user_id]["points"] += points
            self.scores[user_id]["games_played"] += 1
            self.scores[user_id]["placement_sum"] += placement

        self.save_scores()
        await ctx.reply("Results recorded successfully!")

    @commands.command()
    async def leaderboard(self, ctx):
        """Display the leaderboard."""
        if not self.scores:
            await ctx.reply("No scores recorded yet.")
            return

        sorted_scores = sorted(
            self.scores.items(), key=lambda item: item[1]["points"], reverse=True
        )
        embed = discord.Embed(
            title="🏆 Poker Leaderboard 🏆", color=discord.Color.gold()
        )

        for idx, (user_id, data) in enumerate(sorted_scores, start=1):
            avg_placement = data["placement_sum"] / data["games_played"]
            embed.add_field(
                name=f"#{idx} - {data['name']}",
                value=(
                    f"Points: {data['points']} | Games Played: {data['games_played']}\n"
                    f"Avg Placement: {avg_placement:.2f}"
                ),
                inline=False,
            )

        await ctx.reply(embed=embed)

    @commands.command()
    async def reset_leaderboard(self, ctx):
        """Resets the leaderboard (Admin only)."""
        if not ctx.author.guild_permissions.administrator:
            await ctx.reply("Only admins can reset the leaderboard.")
            return

        self.scores = {}
        self.save_scores()
        await ctx.reply("Leaderboard has been reset.")


async def setup(bot):
    await bot.add_cog(Poker(bot))
