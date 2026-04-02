"""
VT grade distribution data loader.

Data source: VT University Data Commons grade distribution CSV.
Since UDC requires VT PID authentication, bundle a pre-exported CSV at data/vt_grades.csv.
To refresh data: log into https://udc.vt.edu/irdata/data/courses/grades and export to CSV.

Expected CSV columns:
    term, subject, course_number, instructor, gpa, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, F, W
"""

import csv
from collections import defaultdict
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "vt_grades.csv"

GRADE_COLS = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F", "W"]

# Cache: { "CS 3114": { "202408": {grade: pct, ...}, ... } }
_cache: dict[str, dict[str, dict[str, float]]] | None = None
_insights_cache: dict[str, dict] | None = None


def _load() -> dict[str, dict[str, dict[str, float]]]:
    global _cache
    if _cache is not None:
        return _cache

    data: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)

    if not DATA_PATH.exists():
        print(f"[vt_data] WARNING: {DATA_PATH} not found. Grade commands will return no data.")
        _cache = {}
        return _cache

    with open(DATA_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            subject = row.get("subject", "").strip().upper()
            number = row.get("course_number", "").strip()
            term = row.get("term", "").strip()
            if not subject or not number or not term:
                continue

            code = f"{subject} {number}"
            grades = {}
            total = 0.0
            raw = {}
            for g in GRADE_COLS:
                try:
                    val = float(row.get(g, 0) or 0)
                except ValueError:
                    val = 0.0
                raw[g] = val
                total += val

            if total > 0:
                grades = {g: round(raw[g] / total * 100, 2) for g in GRADE_COLS}
            else:
                grades = {g: 0.0 for g in GRADE_COLS}

            # Aggregate by term (average across instructors)
            if term not in data[code]:
                data[code][term] = {"_count": 0, **{g: 0.0 for g in GRADE_COLS}}
            entry = data[code][term]
            entry["_count"] += 1
            for g in GRADE_COLS:
                entry[g] += grades[g]

    # Finalize averages
    result: dict[str, dict[str, dict[str, float]]] = {}
    for code, terms in data.items():
        result[code] = {}
        for term, entry in terms.items():
            count = entry["_count"]
            result[code][term] = {g: round(entry[g] / count, 2) for g in GRADE_COLS}

    _cache = result
    return _cache


def get_course_codes() -> list[str]:
    """Return sorted list of all available course codes."""
    return sorted(_load().keys())


def _load_insights() -> dict[str, dict]:
    """Aggregate course-level metrics and instructor rollups for UI summaries."""
    global _insights_cache
    if _insights_cache is not None:
        return _insights_cache

    insights: dict[str, dict] = defaultdict(
        lambda: {
            "terms": set(),
            "sections": 0,
            "gpa_sum": 0.0,
            "gpa_count": 0,
            "a_rate_sum": 0.0,
            "w_rate_sum": 0.0,
            "instructors": defaultdict(
                lambda: {"sections": 0, "a_rate_sum": 0.0, "gpa_sum": 0.0, "gpa_count": 0}
            ),
        }
    )

    if not DATA_PATH.exists():
        _insights_cache = {}
        return _insights_cache

    with open(DATA_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            subject = row.get("subject", "").strip().upper()
            number = row.get("course_number", "").strip()
            term = row.get("term", "").strip()
            instructor = row.get("instructor", "").strip() or "Staff"
            if not subject or not number or not term:
                continue

            code = f"{subject} {number}"
            item = insights[code]
            item["terms"].add(term)
            item["sections"] += 1

            try:
                gpa_val = float(row.get("gpa", 0) or 0)
            except ValueError:
                gpa_val = 0.0

            if gpa_val > 0:
                item["gpa_sum"] += gpa_val
                item["gpa_count"] += 1

            try:
                a_rate = float(row.get("A", 0) or 0) + float(row.get("A-", 0) or 0)
            except ValueError:
                a_rate = 0.0
            try:
                w_rate = float(row.get("W", 0) or 0)
            except ValueError:
                w_rate = 0.0

            item["a_rate_sum"] += a_rate
            item["w_rate_sum"] += w_rate

            instr = item["instructors"][instructor]
            instr["sections"] += 1
            instr["a_rate_sum"] += a_rate
            if gpa_val > 0:
                instr["gpa_sum"] += gpa_val
                instr["gpa_count"] += 1

    finalized: dict[str, dict] = {}
    for code, raw in insights.items():
        sections = raw["sections"]
        avg_gpa = round(raw["gpa_sum"] / raw["gpa_count"], 2) if raw["gpa_count"] else 0.0
        avg_a_rate = round(raw["a_rate_sum"] / sections, 1) if sections else 0.0
        avg_w_rate = round(raw["w_rate_sum"] / sections, 1) if sections else 0.0

        instructor_rows = []
        for name, i in raw["instructors"].items():
            i_sections = i["sections"]
            i_a = round(i["a_rate_sum"] / i_sections, 1) if i_sections else 0.0
            i_gpa = round(i["gpa_sum"] / i["gpa_count"], 2) if i["gpa_count"] else 0.0
            instructor_rows.append(
                {
                    "name": name,
                    "sections": i_sections,
                    "a_rate": i_a,
                    "gpa": i_gpa,
                }
            )

        instructor_rows.sort(key=lambda r: (r["sections"], r["a_rate"]), reverse=True)

        finalized[code] = {
            "terms": len(raw["terms"]),
            "sections": sections,
            "avg_gpa": avg_gpa,
            "a_rate": avg_a_rate,
            "w_rate": avg_w_rate,
            "instructors": instructor_rows,
        }

    _insights_cache = finalized
    return _insights_cache


def query_course(course_code: str, semester: str | None = None) -> tuple[dict[str, float], str] | None:
    """
    Return (grade_distribution_dict, semester_label) for the given course code.
    If semester is None, returns the most recent semester's data.
    Returns None if the course is not found.
    """
    db = _load()
    code = course_code.strip().upper()

    if code not in db:
        return None

    terms = db[code]
    if not terms:
        return None

    if semester and semester in terms:
        return terms[semester], _format_term(semester)

    latest_term = max(terms.keys())
    return terms[latest_term], _format_term(latest_term)


def query_course_insights(course_code: str) -> dict | None:
    """Return aggregated course metrics and top instructors for dashboard-style embeds."""
    db = _load_insights()
    code = course_code.strip().upper()
    return db.get(code)


def _format_term(term: str) -> str:
    """Convert term code like '202408' → 'Fall 2024'."""
    if len(term) == 6:
        year = term[:4]
        month = term[4:]
        seasons = {"01": "Spring", "06": "Summer", "08": "Fall", "12": "Winter"}
        season = seasons.get(month, month)
        return f"{season} {year}"
    return term
