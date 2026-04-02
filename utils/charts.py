import io
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — must be set before pyplot import
import matplotlib.pyplot as plt
import discord

# Refined dark palette
BG_COLOR = "#23262d"
PLOT_BG = "#2b2f38"
BAR_COLOR = "#4f7df0"
BAR_COLOR_2 = "#f07b59"
TEXT_COLOR = "#f2f4f8"
GRID_COLOR = "#4a4f5a"

GRADE_ORDER = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F", "W"]

GRADE_COLORS = {
    "A": "#7cc16b",
    "A-": "#70b963",
    "B+": "#5ba9e8",
    "B": "#4f9bda",
    "B-": "#448fcd",
    "C+": "#e0bf63",
    "C": "#d5ae4a",
    "C-": "#c99d37",
    "D+": "#d7816a",
    "D": "#ca6f58",
    "D-": "#bd5d47",
    "F": "#ae4b3b",
    "W": "#9ca3af",
}


def _apply_dark_theme(fig, ax):
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(PLOT_BG)
    ax.tick_params(colors=TEXT_COLOR)
    ax.xaxis.label.set_color(TEXT_COLOR)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.title.set_color(TEXT_COLOR)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COLOR)
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.7, alpha=0.5)
    ax.set_axisbelow(True)


def generate_grade_bar(course_code: str, grade_data: dict, semester: str = "") -> discord.File:
    """
    Generate a single-course grade distribution bar chart.
    grade_data: {grade_letter: percentage, ...}
    Returns a discord.File ready to attach to a message.
    """
    labels = [g for g in GRADE_ORDER if g in grade_data]
    values = [grade_data[g] for g in labels]

    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    colors = [GRADE_COLORS.get(label, BAR_COLOR) for label in labels]
    bars = ax.bar(labels, values, color=colors, width=0.64, zorder=2)

    # Label bars with percentage values
    for bar, val in zip(bars, values):
        if val >= 2.0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.5,
                f"{val:.0f}%",
                ha="center", va="bottom",
                color=TEXT_COLOR, fontsize=8, fontweight="bold"
            )

    title = f"Grade Distribution | {course_code.upper()}"
    if semester:
        title += f" ({semester})"
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Grade", fontsize=11)
    ax.set_ylabel("Students (%)", fontsize=11)
    ax.set_ylim(0, max(values) * 1.2 + 4 if values else 100)

    _apply_dark_theme(fig, ax)
    plt.tight_layout(pad=1.2)

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

    fig, ax = plt.subplots(figsize=(11, 5.2))
    bars1 = ax.bar([i - width / 2 for i in x], vals1, width, color=BAR_COLOR, label=course1.upper(), zorder=2)
    bars2 = ax.bar([i + width / 2 for i in x], vals2, width, color=BAR_COLOR_2, label=course2.upper(), zorder=2)

    for bar, val in zip(bars1, vals1):
        if val >= 3:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.4,
                    f"{val:.0f}%", ha="center", va="bottom", color=TEXT_COLOR, fontsize=7.5)
    for bar, val in zip(bars2, vals2):
        if val >= 3:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.4,
                    f"{val:.0f}%", ha="center", va="bottom", color=TEXT_COLOR, fontsize=7.5)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_xlabel("Grade", fontsize=11)
    ax.set_ylabel("Students (%)", fontsize=11)
    ax.set_title(f"Grade Comparison | {course1.upper()} vs {course2.upper()}", fontsize=13, fontweight="bold", pad=10)

    ax.legend(facecolor=PLOT_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR, fontsize=10)
    _apply_dark_theme(fig, ax)
    plt.tight_layout(pad=1.2)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, facecolor=BG_COLOR)
    plt.close(fig)
    buf.seek(0)
    return discord.File(buf, filename="compare.png")
