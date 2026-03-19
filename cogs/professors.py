import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import ratemyprofessor

MAROON = 0x861F41
ORANGE = 0xE5751F

# Virginia Tech's school object is fetched once at startup
_vt_school = None


def _get_vt_school():
    global _vt_school
    if _vt_school is None:
        _vt_school = ratemyprofessor.get_school_by_name("Virginia Tech")
    return _vt_school


def _rating_bar(rating: float, max_rating: float = 5.0, length: int = 10) -> str:
    """Build a simple text progress bar for ratings."""
    filled = round((rating / max_rating) * length)
    return "█" * filled + "░" * (length - filled)


def _difficulty_label(score: float) -> str:
    if score < 2.0:
        return "Easy"
    elif score < 3.0:
        return "Moderate"
    elif score < 4.0:
        return "Challenging"
    else:
        return "Very Hard"


class ProfessorsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="professor",
        description="Look up a Virginia Tech professor's Rate My Professor rating."
    )
    @app_commands.describe(name="Professor's name (e.g. 'Godmar Back')")
    async def professor(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(thinking=True)

        try:
            # RMP is a blocking library — run in thread pool to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            prof = await loop.run_in_executor(
                None, self._fetch_professor, name
            )
        except Exception as e:
            await interaction.followup.send(
                embed=_error_embed(f"Could not reach Rate My Professor: {e}"),
                ephemeral=True
            )
            return

        if prof is None:
            await interaction.followup.send(
                embed=_not_found_embed(name),
                ephemeral=True
            )
            return

        embed = _build_professor_embed(prof)
        await interaction.followup.send(embed=embed)

    def _fetch_professor(self, name: str):
        school = _get_vt_school()
        if school is None:
            return None
        return ratemyprofessor.get_professor_by_school_and_name(school, name)


def _build_professor_embed(prof) -> discord.Embed:
    rating = getattr(prof, "rating", None)
    difficulty = getattr(prof, "difficulty", None)
    would_take_again = getattr(prof, "would_take_again", None)
    department = getattr(prof, "department", "CS")
    num_ratings = getattr(prof, "num_ratings", 0)

    # Color based on rating quality
    if rating is None:
        color = discord.Color.greyple()
    elif rating >= 4.0:
        color = 0x57F287  # green
    elif rating >= 3.0:
        color = ORANGE
    else:
        color = 0xED4245  # red

    embed = discord.Embed(
        title=f"Prof. {prof.name}",
        description=f"**{department}** · Virginia Tech",
        color=color,
        url="https://www.ratemyprofessors.com"
    )

    if rating is not None:
        embed.add_field(
            name="Overall Rating",
            value=f"`{_rating_bar(rating)}` **{rating:.1f} / 5.0**",
            inline=False
        )
    else:
        embed.add_field(name="Overall Rating", value="N/A", inline=False)

    if difficulty is not None:
        embed.add_field(
            name="Difficulty",
            value=f"`{_rating_bar(difficulty)}` **{difficulty:.1f} / 5.0**  ({_difficulty_label(difficulty)})",
            inline=False
        )

    if would_take_again is not None:
        pct = round(would_take_again)
        embed.add_field(
            name="Would Take Again",
            value=f"**{pct}%** of students",
            inline=True
        )

    if num_ratings:
        embed.add_field(
            name="Total Ratings",
            value=str(num_ratings),
            inline=True
        )

    embed.set_footer(text="Data from ratemyprofessors.com — ratings may vary by semester")
    return embed


def _not_found_embed(name: str) -> discord.Embed:
    return discord.Embed(
        title=f"Professor not found: {name}",
        description=(
            "No results on Rate My Professor for this name at Virginia Tech.\n"
            "Try their full name, e.g. `/professor Godmar Back`."
        ),
        color=discord.Color.red()
    )


def _error_embed(message: str) -> discord.Embed:
    return discord.Embed(
        title="Error",
        description=message,
        color=discord.Color.red()
    )


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfessorsCog(bot))
