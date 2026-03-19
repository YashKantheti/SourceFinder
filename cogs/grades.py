import discord
from discord import app_commands
from discord.ext import commands
from utils import vt_data, charts

MAROON = 0x861F41
ORANGE = 0xE5751F


class GradesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="grades",
        description="Show grade distribution for a VT CS course (e.g. CS 3114)."
    )
    @app_commands.describe(course="Course code, e.g. CS 3114 or ECE 2574")
    async def grades(self, interaction: discord.Interaction, course: str):
        await interaction.response.defer(thinking=True)

        result = vt_data.query_course(course)
        if result is None:
            available = ", ".join(vt_data.get_course_codes()[:15])
            await interaction.followup.send(
                embed=_not_found_embed(
                    course,
                    f"Available courses include: {available} …\nUse `/grades CS 3114` format."
                ),
                ephemeral=True
            )
            return

        grade_data, semester = result
        chart_file = charts.generate_grade_bar(course, grade_data, semester)

        embed = discord.Embed(
            title=f"{course.upper()} — Grade Distribution",
            description=_grade_summary(grade_data),
            color=ORANGE,
        )
        embed.set_image(url="attachment://grades.png")
        embed.set_footer(text=f"Source: VT DataCommons  •  {semester}")
        await interaction.followup.send(embed=embed, file=chart_file)

    @grades.autocomplete("course")
    async def grades_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        codes = vt_data.get_course_codes()
        current_up = current.upper()
        matches = [c for c in codes if current_up in c][:25]
        return [app_commands.Choice(name=c, value=c) for c in matches]

    @app_commands.command(
        name="compare",
        description="Compare grade distributions of two VT courses side by side."
    )
    @app_commands.describe(
        course1="First course code (e.g. CS 2114)",
        course2="Second course code (e.g. CS 3114)"
    )
    async def compare(
        self,
        interaction: discord.Interaction,
        course1: str,
        course2: str
    ):
        await interaction.response.defer(thinking=True)

        r1 = vt_data.query_course(course1)
        r2 = vt_data.query_course(course2)

        missing = []
        if r1 is None:
            missing.append(course1.upper())
        if r2 is None:
            missing.append(course2.upper())
        if missing:
            await interaction.followup.send(
                embed=_not_found_embed(", ".join(missing), "Check the course code and try again."),
                ephemeral=True
            )
            return

        data1, sem1 = r1
        data2, sem2 = r2
        chart_file = charts.generate_compare_bar(course1, data1, course2, data2, sem1, sem2)

        embed = discord.Embed(
            title=f"Grade Comparison — {course1.upper()} vs {course2.upper()}",
            color=MAROON,
        )
        embed.add_field(
            name=f"{course1.upper()}  ({sem1})",
            value=_grade_summary(data1),
            inline=True
        )
        embed.add_field(
            name=f"{course2.upper()}  ({sem2})",
            value=_grade_summary(data2),
            inline=True
        )
        embed.set_image(url="attachment://compare.png")
        embed.set_footer(text="Source: VT DataCommons")
        await interaction.followup.send(embed=embed, file=chart_file)

    @compare.autocomplete("course1")
    @compare.autocomplete("course2")
    async def compare_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        codes = vt_data.get_course_codes()
        current_up = current.upper()
        matches = [c for c in codes if current_up in c][:25]
        return [app_commands.Choice(name=c, value=c) for c in matches]


def _grade_summary(grade_data: dict) -> str:
    """Build a short text summary of the most relevant grade buckets."""
    a_pct = grade_data.get("A", 0) + grade_data.get("A-", 0)
    b_pct = grade_data.get("B+", 0) + grade_data.get("B", 0) + grade_data.get("B-", 0)
    c_pct = grade_data.get("C+", 0) + grade_data.get("C", 0) + grade_data.get("C-", 0)
    d_f_pct = (
        grade_data.get("D+", 0) + grade_data.get("D", 0) +
        grade_data.get("D-", 0) + grade_data.get("F", 0)
    )
    w_pct = grade_data.get("W", 0)
    lines = [
        f"**A/A-:** {a_pct:.1f}%",
        f"**B range:** {b_pct:.1f}%",
        f"**C range:** {c_pct:.1f}%",
        f"**D/F:** {d_f_pct:.1f}%",
        f"**W (withdraw):** {w_pct:.1f}%",
    ]
    return "\n".join(lines)


def _not_found_embed(course: str, hint: str = "") -> discord.Embed:
    embed = discord.Embed(
        title=f"Course not found: {course.upper()}",
        description=hint or "Make sure the course code is correct.",
        color=discord.Color.red()
    )
    return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(GradesCog(bot))
