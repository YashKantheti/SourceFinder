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
        if not await _safe_defer(interaction):
            return

        result = vt_data.query_course(course)
        if result is None:
            available = ", ".join(vt_data.get_course_codes()[:15])
            await _safe_followup_send(
                interaction,
                embed=_not_found_embed(
                    course,
                    f"Available courses include: {available} …\nUse `/grades CS 3114` format."
                ),
                ephemeral=True
            )
            return

        grade_data, semester = result
        insights = vt_data.query_course_insights(course)
        chart_file = charts.generate_grade_bar(course, grade_data, semester)

        embed = discord.Embed(
            title=f"{course.upper()} - Grade Snapshot",
            description=_overview_line(grade_data, insights),
            color=ORANGE,
        )
        embed.add_field(
            name="Grade Breakdown",
            value=_grade_summary(grade_data),
            inline=False,
        )

        if insights:
            embed.add_field(name="Key Metrics", value=_kpi_cards(insights), inline=False)
            embed.add_field(name="By Instructor", value=_instructor_table(insights), inline=False)

        embed.set_image(url="attachment://grades.png")
        embed.set_footer(text=f"Source: VT DataCommons | {semester}")
        await _safe_followup_send(interaction, embed=embed, file=chart_file)

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
        if not await _safe_defer(interaction):
            return

        r1 = vt_data.query_course(course1)
        r2 = vt_data.query_course(course2)

        missing = []
        if r1 is None:
            missing.append(course1.upper())
        if r2 is None:
            missing.append(course2.upper())
        if missing:
            await _safe_followup_send(
                interaction,
                embed=_not_found_embed(", ".join(missing), "Check the course code and try again."),
                ephemeral=True
            )
            return

        data1, sem1 = r1
        data2, sem2 = r2
        chart_file = charts.generate_compare_bar(course1, data1, course2, data2, sem1, sem2)

        embed = discord.Embed(
            title=f"Comparison: {course1.upper()} vs {course2.upper()}",
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
        embed.set_footer(text="Source: VT DataCommons | Tip: pair one heavy and one moderate course")
        await _safe_followup_send(interaction, embed=embed, file=chart_file)

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
    """Build compact fixed-width summary for primary grade buckets."""
    a_pct = grade_data.get("A", 0) + grade_data.get("A-", 0)
    b_pct = grade_data.get("B+", 0) + grade_data.get("B", 0) + grade_data.get("B-", 0)
    c_pct = grade_data.get("C+", 0) + grade_data.get("C", 0) + grade_data.get("C-", 0)
    d_f_pct = (
        grade_data.get("D+", 0) + grade_data.get("D", 0) +
        grade_data.get("D-", 0) + grade_data.get("F", 0)
    )
    w_pct = grade_data.get("W", 0)
    lines = [
        _bar_line("A", a_pct),
        _bar_line("B", b_pct),
        _bar_line("C", c_pct),
        _bar_line("D/F", d_f_pct),
        _bar_line("W", w_pct),
    ]
    return "```\n" + "\n".join(lines) + "\n```"


def _bar_line(label: str, pct: float) -> str:
    units = max(0, min(20, int(round(pct / 5))))
    return f"{label:<3} | {'#' * units}{'-' * (20 - units)} | {pct:>5.1f}%"


def _overview_line(grade_data: dict, insights: dict | None) -> str:
    a_rate = grade_data.get("A", 0) + grade_data.get("A-", 0)
    w_rate = grade_data.get("W", 0)
    est_gpa = _estimate_gpa(grade_data)

    if not insights:
        return f"All sections summary | Est GPA `{est_gpa:.2f}` | A-rate `{a_rate:.1f}%` | Withdraw `{w_rate:.1f}%`"

    return (
        f"Across `{insights['terms']}` terms and `{insights['sections']}` sections | "
        f"Avg GPA `{insights['avg_gpa']:.2f}` | A-rate `{a_rate:.1f}%` | Withdraw `{w_rate:.1f}%`"
    )


def _kpi_cards(insights: dict) -> str:
    return "```\n" + (
        f"AVG GPA   {insights['avg_gpa']:.2f}\n"
        f"A RATE    {insights['a_rate']:.1f}%\n"
        f"WITHDRAW  {insights['w_rate']:.1f}%"
    ) + "\n```"


def _instructor_table(insights: dict) -> str:
    rows = insights.get("instructors", [])[:4]
    if not rows:
        return "No instructor-level rows available."

    header = f"{'Instructor':<16} {'Sec':>3} {'A%':>5} {'GPA':>5}"
    body = [header, "-" * len(header)]
    for r in rows:
        name = (r["name"] or "Staff")[:16]
        body.append(f"{name:<16} {r['sections']:>3} {r['a_rate']:>5.1f} {r['gpa']:>5.2f}")
    return "```\n" + "\n".join(body) + "\n```"


def _estimate_gpa(grade_data: dict) -> float:
    weights = {
        "A": 4.0,
        "A-": 3.7,
        "B+": 3.3,
        "B": 3.0,
        "B-": 2.7,
        "C+": 2.3,
        "C": 2.0,
        "C-": 1.7,
        "D+": 1.3,
        "D": 1.0,
        "D-": 0.7,
        "F": 0.0,
    }
    total = 0.0
    for grade, weight in weights.items():
        total += (grade_data.get(grade, 0) / 100.0) * weight
    return total


def _not_found_embed(course: str, hint: str = "") -> discord.Embed:
    embed = discord.Embed(
        title=f"Course not found: {course.upper()}",
        description=hint or "Make sure the course code is correct.",
        color=discord.Color.red()
    )
    return embed


async def _safe_defer(interaction: discord.Interaction) -> bool:
    """Defer safely; return False if the interaction is already invalid/expired."""
    try:
        await interaction.response.defer(thinking=True)
        return True
    except discord.NotFound:
        return False
    except discord.InteractionResponded:
        return True


async def _safe_followup_send(interaction: discord.Interaction, **kwargs) -> bool:
    """Send follow-up safely; return False if the interaction token is no longer valid."""
    try:
        await interaction.followup.send(**kwargs)
        return True
    except discord.NotFound:
        return False


async def setup(bot: commands.Bot):
    await bot.add_cog(GradesCog(bot))
