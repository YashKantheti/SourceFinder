import discord
from discord import app_commands
from discord.ext import commands
from utils.rmp import search_professor, ProfessorResult

MAROON = 0x861F41
ORANGE = 0xE5751F


def _rating_bar(rating: float, max_rating: float = 5.0, length: int = 10) -> str:
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
            prof = await search_professor(name)
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


def _build_professor_embed(prof: ProfessorResult) -> discord.Embed:
    rating = prof.rating
    difficulty = prof.difficulty
    would_take_again = prof.would_take_again

    if rating is None:
        color = discord.Color.greyple()
    elif rating >= 4.0:
        color = 0x57F287   # green
    elif rating >= 3.0:
        color = ORANGE
    else:
        color = 0xED4245   # red

    embed = discord.Embed(
        title=f"Prof. {prof.name}",
        description=f"**{prof.department}** · Virginia Tech",
        color=color,
        url=prof.url,
    )

    if rating is not None:
        embed.add_field(
            name="Overall Rating",
            value=f"`{_rating_bar(rating)}` **{rating:.1f} / 5.0**",
            inline=False,
        )
    else:
        embed.add_field(name="Overall Rating", value="No ratings yet", inline=False)

    if difficulty is not None:
        embed.add_field(
            name="Difficulty",
            value=f"`{_rating_bar(difficulty)}` **{difficulty:.1f} / 5.0**  ({_difficulty_label(difficulty)})",
            inline=False,
        )

    if would_take_again is not None and would_take_again >= 0:
        embed.add_field(
            name="Would Take Again",
            value=f"**{round(would_take_again)}%** of students",
            inline=True,
        )

    if prof.num_ratings:
        embed.add_field(name="Total Ratings", value=str(prof.num_ratings), inline=True)

    embed.set_footer(text="Data from ratemyprofessors.com — ratings may vary by semester")
    return embed


def _not_found_embed(name: str) -> discord.Embed:
    return discord.Embed(
        title=f"Professor not found: {name}",
        description=(
            "No results on Rate My Professor for this name at Virginia Tech.\n"
            "Try their full name, e.g. `/professor Godmar Back`."
        ),
        color=discord.Color.red(),
    )


def _error_embed(message: str) -> discord.Embed:
    return discord.Embed(title="Error", description=message, color=discord.Color.red())


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfessorsCog(bot))
