import io
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — must be set before pyplot import
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import discord

# Discord dark theme colors
BG_COLOR = "#2f3136"
BAR_COLOR = "#5865f2"  # Discord blurple
BAR_COLOR_2 = "#eb459e"  # Discord pink (for compare charts)
TEXT_COLOR = "#ffffff"
GRID_COLOR = "#40444b"

GRADE_ORDER = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F", "W"]


def _apply_dark_theme(fig, ax):
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.tick_params(colors=TEXT_COLOR)
    ax.xaxis.label.set_color(TEXT_COLOR)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.title.set_color(TEXT_COLOR)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COLOR)
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)


def generate_grade_bar(course_code: str, grade_data: dict, semester: str = "") -> discord.File:
    """
    Generate a single-course grade distribution bar chart.
    grade_data: {grade_letter: percentage, ...}
    Returns a discord.File ready to attach to a message.
    """
    labels = [g for g in GRADE_ORDER if g in grade_data]
    values = [grade_data[g] for g in labels]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.bar(labels, values, color=BAR_COLOR, width=0.6, zorder=2)

    # Label bars with percentage values
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.5,
                f"{val:.1f}%",
                ha="center", va="bottom",
                color=TEXT_COLOR, fontsize=8.5, fontweight="bold"
            )

    title = f"Grade Distribution — {course_code.upper()}"
    if semester:
        title += f"  ({semester})"
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Grade", fontsize=11)
    ax.set_ylabel("Students (%)", fontsize=11)
    ax.set_ylim(0, max(values) * 1.2 + 5 if values else 100)

    _apply_dark_theme(fig, ax)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, facecolor=BG_COLOR)
    plt.close(fig)
    buf.seek(0)
    return discord.File(buf, filename="grades.png")


def generate_compare_bar(
    course1: str, data1: dict,
    course2: str, data2: dict,
    semester1: str = "", semester2: str = ""
) -> discord.File:
    """
    Generate a grouped bar chart comparing grade distributions of two courses.
    """
    labels = [g for g in GRADE_ORDER if g in data1 or g in data2]
    vals1 = [data1.get(g, 0) for g in labels]
    vals2 = [data2.get(g, 0) for g in labels]

    x = range(len(labels))
    width = 0.38

    fig, ax = plt.subplots(figsize=(11, 5))
    bars1 = ax.bar([i - width / 2 for i in x], vals1, width, color=BAR_COLOR, label=course1.upper(), zorder=2)
    bars2 = ax.bar([i + width / 2 for i in x], vals2, width, color=BAR_COLOR_2, label=course2.upper(), zorder=2)

    for bar, val in zip(bars1, vals1):
        if val > 1.5:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.4,
                    f"{val:.0f}%", ha="center", va="bottom", color=TEXT_COLOR, fontsize=7.5)
    for bar, val in zip(bars2, vals2):
        if val > 1.5:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.4,
                    f"{val:.0f}%", ha="center", va="bottom", color=TEXT_COLOR, fontsize=7.5)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_xlabel("Grade", fontsize=11)
    ax.set_ylabel("Students (%)", fontsize=11)
    ax.set_title(f"Grade Comparison — {course1.upper()} vs {course2.upper()}", fontsize=13, fontweight="bold", pad=12)

    legend = ax.legend(facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR, fontsize=10)
    _apply_dark_theme(fig, ax)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, facecolor=BG_COLOR)
    plt.close(fig)
    buf.seek(0)
    return discord.File(buf, filename="compare.png")
