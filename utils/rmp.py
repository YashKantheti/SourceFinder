"""
Direct Rate My Professor GraphQL scraper.

The ratemyprofessor pip package is broken (returns 403) due to missing browser headers.
This module queries RMP's internal GraphQL API directly with proper headers.
"""

import base64
import ssl
import certifi
import aiohttp

VT_SCHOOL_ID = 1349  # Virginia Tech on RMP
_RMP_GQL_URL = "https://www.ratemyprofessors.com/graphql"

_SEARCH_QUERY = """
query TeacherSearch($text: String!, $schoolID: ID!) {
  search: newSearch {
    teachers(query: {text: $text, schoolID: $schoolID}, first: 10) {
      edges {
        node {
          id
          firstName
          lastName
          department
          avgRating
          avgDifficulty
          wouldTakeAgainPercent
          numRatings
          legacyId
        }
      }
    }
  }
}
"""


# Check if RMP has specific auth requirements - if not, we can strip these headers
# The current test credentials ("test:test") are breaking the API calls
_HEADERS_NO_AUTH = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.ratemyprofessors.com/",
}


class ProfessorResult:
    def __init__(self, node: dict):
        self.name = f"{node.get('firstName', '')} {node.get('lastName', '')}".strip()
        self.department = node.get("department") or "N/A"
        self.rating = node.get("avgRating")          # float or None
        self.difficulty = node.get("avgDifficulty")  # float or None
        self.would_take_again = node.get("wouldTakeAgainPercent")  # float or None (0–100)
        self.num_ratings = node.get("numRatings", 0)
        legacy_id = node.get("legacyId")
        self.url = f"https://www.ratemyprofessors.com/professor/{legacy_id}" if legacy_id else "https://www.ratemyprofessors.com"


async def search_professor(name: str, school_id: int = VT_SCHOOL_ID) -> ProfessorResult | None:
    """
    Search RMP for a professor by name at the given school.
    Returns the result with the most ratings, or None if not found.
    """
    school_node_id = base64.b64encode(f"School-{school_id}".encode()).decode()

    payload = {
        "query": _SEARCH_QUERY,
        "variables": {"text": name, "schoolID": school_node_id},
    }

    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_ctx)
    async with aiohttp.ClientSession(headers=_HEADERS_NO_AUTH, connector=connector) as session:
        async with session.post(_RMP_GQL_URL, json=payload) as resp:
            if resp.status != 200:
                raise RuntimeError(f"RMP returned HTTP {resp.status}")
            data = await resp.json(content_type=None)

    edges = (
        data.get("data", {})
            .get("search", {})
            .get("teachers", {})
            .get("edges", [])
    )

    if not edges:
        return None

    # Pick the professor with the most ratings (best match heuristic)
    best = max(edges, key=lambda e: e["node"].get("numRatings", 0))
    return ProfessorResult(best["node"])
