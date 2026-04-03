"""
Security Log Analyzer — FastAPI backend
Analyzes uploaded log files with OpenRouter and maps findings to MITRE ATT&CK.
"""

import json
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from openai import OpenAI, APIError
from mitreattack.stix20 import MitreAttackData
from pydantic import BaseModel

load_dotenv()
mitre_data: MitreAttackData = None
openrouter_client: OpenAI = None
system_prompt: str = None

BUNDLE_PATH = os.path.join(os.path.dirname(__file__), "enterprise-attack.json")


def build_system_prompt(mitre: MitreAttackData) -> str:
    """Build dynamic system prompt with techniques from MITRE database."""
    techniques = mitre.get_objects_by_type("attack-pattern")

    # Group techniques by tactic for better organization
    by_tactic: dict[str, list] = {}
    for tech in techniques:
        if hasattr(tech, "kill_chain_phases") and tech.kill_chain_phases:
            for phase in tech.kill_chain_phases:
                if phase.kill_chain_name == "mitre-attack":
                    tactic = phase.phase_name.replace("-", " ").title()
                    if tactic not in by_tactic:
                        by_tactic[tactic] = []
                    by_tactic[tactic].append(tech)
                    break

    # Build technique reference section
    technique_ref = "AVAILABLE MITRE ATT&CK TECHNIQUES (sample):\n"
    for tactic in sorted(by_tactic.keys()):
        tactic_techniques = by_tactic[tactic][:5]  # Limit to 5 per tactic for prompt size
        technique_ref += f"\n{tactic}:\n"
        for tech in tactic_techniques:
            attack_id = ""
            if hasattr(tech, "external_references"):
                for ref in tech.external_references:
                    if ref.get("source_name") == "mitre-attack":
                        attack_id = ref.get("external_id", "")
                        break
            if attack_id:
                desc = (tech.description or "")[:100].strip()
                technique_ref += f"  - {attack_id}: {tech.name} ({desc}...)\n"

    return f"""You are a cybersecurity threat analyst specializing in log analysis and incident response. You analyze log data and identify coordinated ATTACK PATTERNS — groups of correlated events that together indicate a specific threat behavior or attack campaign.

TASK: Identify attack patterns in the provided logs. Each pattern should represent a coherent attack story or threat behavior, grouping related events together rather than flagging individual anomalies in isolation.

SEVERITY LEVELS:
- CRITICAL: Confirmed attack with clear evidence — active exploitation, successful breach, lateral movement, C2 communication
- HIGH: Strong behavioral indicators requiring immediate attention — brute force with valid usernames, suspicious internal pivoting
- MEDIUM: Suspicious activity warranting investigation — policy violations, unusual access patterns
- LOW: Anomalous behavior that could be malicious or benign

INSTRUCTIONS:
- Group related log events into named attack patterns
- Pattern names should be concise and descriptive, e.g.: "Credential stuffing — external origin", "Lateral movement — single host pivoting", "SSH brute force — internal origin"
- Assign severity based on the risk level and certainty of the pattern
- Identify all applicable MITRE ATT&CK technique IDs (prefer sub-techniques like T1110.004 over T1110)
- Use ONLY real, published MITRE ATT&CK Enterprise technique IDs — do not invent IDs
- Extract exact log lines as evidence events (copy them verbatim from the log)
- Classify IP addresses:
  - External: NOT in private ranges (10.x.x.x, 172.16-31.x.x, 192.168.x.x)
  - Internal: IN private ranges or hostname-only addresses
- If no genuine security threats exist, return []

{technique_ref}

RESPONSE FORMAT:
Respond with ONLY a valid JSON array — no explanation, no markdown, no preamble.
Each element must have exactly these fields:
[
  {{
    "pattern_name": "Credential stuffing — external origin",
    "severity": "CRITICAL",
    "technique_ids": ["T1110.004"],
    "description": "2-3 sentence narrative explaining what happened, why it is alarming, and what the attacker may have accomplished or be attempting.",
    "events": ["09:01:44 | 203.0.113.12 -> 10.0.0.5 | HTTPS 443 | DENY | jdoe_test"],
    "external_ips": ["203.0.113.12"],
    "internal_hosts": []
  }}
]"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    global mitre_data, openrouter_client, system_prompt

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        raise RuntimeError(
            "OpenRouter API Key error, check .env file"
        )

    if not os.path.exists(BUNDLE_PATH):
        raise RuntimeError(
            "STIX bundle not found. Run: python setup.py"
        )

    print("Loading MITRE ATT&CK data...")
    mitre_data = MitreAttackData(stix_filepath=BUNDLE_PATH)
    print("MITRE data loaded.")

    print("Building dynamic system prompt from MITRE data...")
    system_prompt = build_system_prompt(mitre_data)

    openrouter_client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    yield


app = FastAPI(title="Security Log Analyzer", lifespan=lifespan)


class AttackPattern(BaseModel):
    pattern_name: str
    severity: str           # CRITICAL, HIGH, MEDIUM, LOW
    technique_ids: list[str]
    technique_names: list[str]
    description: str
    events: list[str]
    external_ips: list[str]
    internal_hosts: list[str]
    mitre_urls: list[str]


class AnalysisResponse(BaseModel):
    filename: str
    file_size_bytes: int
    chunks_analyzed: int
    patterns: list[AttackPattern]
    critical_count: int
    external_ip_count: int
    internal_pivot_count: int
    raw_log_preview: str


def build_user_message(chunk: str, chunk_num: int, total_chunks: int) -> str:
    header = ""
    if total_chunks > 1:
        header = f"[LOG CHUNK {chunk_num} of {total_chunks}]\n\n"
    return f"{header}Analyze this log content for security threats:\n\n```\n{chunk}\n```"


# Core analysis

def normalize_log_content(raw_bytes: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    text = raw_bytes.decode("utf-8", errors="replace")
    if ext == "json":
        try:
            return json.dumps(json.loads(text), indent=2)
        except json.JSONDecodeError:
            return text
    return text


CHUNK_SIZE_LINES = 800
CHUNK_OVERLAP_LINES = 50
SINGLE_CHUNK_THRESHOLD_CHARS = 100_000


def chunk_log(content: str) -> list[str]:
    if len(content) <= SINGLE_CHUNK_THRESHOLD_CHARS:
        return [content]
    lines = content.splitlines()
    chunks: list[str] = []
    step = CHUNK_SIZE_LINES - CHUNK_OVERLAP_LINES
    i = 0
    while i < len(lines):
        chunk_lines = lines[i: i + CHUNK_SIZE_LINES]
        chunks.append("\n".join(chunk_lines))
        i += step
    return chunks


def analyze_chunk(chunk: str, chunk_num: int, total: int) -> list[dict]:
    try:
        response = openrouter_client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": build_user_message(chunk, chunk_num, total)},
            ],
            temperature=0,
            max_tokens=4096,
        )
    except APIError as exc:
        if "quota" in str(exc).lower() or "rate limit" in str(exc).lower():
            raise HTTPException(
                status_code=503,
                detail="Rate limited. Wait a moment, then retry.",
            ) from exc
        raise HTTPException(
            status_code=502,
            detail="Request failed. Check your API key and network connectivity.",
        ) from exc
    raw = response.choices[0].message.content or ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start: end + 1])
            except json.JSONDecodeError:
                pass
    return []


def build_mitre_url(technique_id: str) -> str:
    parts = technique_id.split(".")
    if len(parts) == 2:
        return f"https://attack.mitre.org/techniques/{parts[0]}/{parts[1]}/"
    return f"https://attack.mitre.org/techniques/{parts[0]}/"


def enrich_pattern(raw: dict) -> AttackPattern | None:
    pattern_name = raw.get("pattern_name", "").strip()
    if not pattern_name:
        return None

    technique_ids_raw = raw.get("technique_ids", [])
    if isinstance(technique_ids_raw, str):
        technique_ids_raw = [technique_ids_raw]

    valid_ids: list[str] = []
    valid_names: list[str] = []
    valid_urls: list[str] = []

    for tid in technique_ids_raw:
        tid = tid.strip().upper()
        if not tid:
            continue
        technique = mitre_data.get_object_by_attack_id(attack_id=tid, stix_type="attack-pattern")
        if technique:
            valid_ids.append(tid)
            valid_names.append(technique.name)
            valid_urls.append(build_mitre_url(tid))

    severity = raw.get("severity", "MEDIUM").upper()
    if severity not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        severity = "MEDIUM"

    events = raw.get("events", [])
    if isinstance(events, str):
        events = [events]

    external_ips = raw.get("external_ips", [])
    if isinstance(external_ips, str):
        external_ips = [external_ips]

    internal_hosts = raw.get("internal_hosts", [])
    if isinstance(internal_hosts, str):
        internal_hosts = [internal_hosts]

    return AttackPattern(
        pattern_name=pattern_name,
        severity=severity,
        technique_ids=valid_ids,
        technique_names=valid_names,
        description=raw.get("description", ""),
        events=events,
        external_ips=external_ips,
        internal_hosts=internal_hosts,
        mitre_urls=valid_urls,
    )


SEVERITY_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def deduplicate_patterns(patterns: list[AttackPattern]) -> list[AttackPattern]:
    best: dict[str, AttackPattern] = {}
    for p in patterns:
        key = p.pattern_name.lower().strip()
        existing = best.get(key)
        if existing is None:
            best[key] = p
        elif SEVERITY_RANK.get(p.severity, 0) > SEVERITY_RANK.get(existing.severity, 0):
            best[key] = p
    return sorted(
        best.values(),
        key=lambda x: (-SEVERITY_RANK.get(x.severity, 0), x.pattern_name),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
def health():
    return {"status": "ok", "mitre_loaded": mitre_data is not None}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_log(file: UploadFile = File(...)):
    contents = await file.read()

    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    text = normalize_log_content(contents, file.filename or "upload.txt")
    chunks = chunk_log(text)

    all_patterns: list[AttackPattern] = []
    for i, chunk in enumerate(chunks, start=1):
        raw_results = analyze_chunk(chunk, i, len(chunks))
        for raw in raw_results:
            pattern = enrich_pattern(raw)
            if pattern is not None:
                all_patterns.append(pattern)

    final_patterns = deduplicate_patterns(all_patterns)

    unique_external_ips: set[str] = set()
    unique_internal_hosts: set[str] = set()
    for p in final_patterns:
        unique_external_ips.update(p.external_ips)
        unique_internal_hosts.update(p.internal_hosts)

    critical_count = sum(1 for p in final_patterns if p.severity == "CRITICAL")

    return AnalysisResponse(
        filename=file.filename or "upload.txt",
        file_size_bytes=len(contents),
        chunks_analyzed=len(chunks),
        patterns=final_patterns,
        critical_count=critical_count,
        external_ip_count=len(unique_external_ips),
        internal_pivot_count=len(unique_internal_hosts),
        raw_log_preview=text[:500],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
