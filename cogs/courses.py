import discord
from discord import app_commands
from discord.ext import commands
from utils import ai_client

LEVEL_CHOICES = [
    app_commands.Choice(name="Freshman", value="freshman"),
    app_commands.Choice(name="Sophomore", value="sophomore"),
    app_commands.Choice(name="Junior", value="junior"),
    app_commands.Choice(name="Senior", value="senior"),
    app_commands.Choice(name="Graduate", value="graduate"),
]

MAROON = 0x861F41   # VT maroon
ORANGE = 0xE5751F   # VT orange


class CoursesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="recommend",
        description="Get AI-powered course recommendations based on your interests and year."
    )
    @app_commands.describe(
        interests="What topics or skills interest you? (e.g. 'machine learning, web dev, systems')",
        level="Your current academic level"
    )
    @app_commands.choices(level=LEVEL_CHOICES)
    async def recommend(
        self,
        interaction: discord.Interaction,
        interests: str,
        level: app_commands.Choice[str]
    ):
        await interaction.response.defer(thinking=True)

        try:
            result = await ai_client.get_course_recommendations(interests, level.value)
        except Exception as e:
            await interaction.followup.send(
                embed=_error_embed(f"AI service error: {e}"),
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Course Recommendations",
            description=result,
            color=MAROON,
        )
        embed.set_footer(text=f"For a {level.name} interested in: {interests}")
        embed.set_author(
            name="CourseCompass AI Advisor",
            icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/1/1f/Virginia_Tech_seal.svg/240px-Virginia_Tech_seal.svg.png"
        )
        await interaction.followup.send(embed=embed)


def _error_embed(message: str) -> discord.Embed:
    return discord.Embed(
        title="Something went wrong",
        description=message,
        color=discord.Color.red()
    )


async def setup(bot: commands.Bot):
    await bot.add_cog(CoursesCog(bot))
