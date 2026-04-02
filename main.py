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

    return f"""You are a cybersecurity threat analyst specializing in log analysis and threat detection. You are trained to identify security threats from log data and map them to specific MITRE ATT&CK techniques based on the evidence provided in the logs.

Your task is to analyze log data and identify security threats, mapping each finding to a specific MITRE ATT&CK technique.

INSTRUCTIONS:
- Analyze the provided log content for indicators of compromise, suspicious activity, or active attacks.
- For each threat found, identify the single most specific MITRE ATT&CK technique ID.
- Prefer sub-techniques (e.g., T1059.001) over parent techniques (e.g., T1059) when the evidence is specific enough.
- Use ONLY real, published MITRE ATT&CK Enterprise technique IDs. Do not invent IDs.
- Reference the techniques below when identifying threats.
- If no genuine security threats are found, return an empty array [].
- Confidence levels:
  - "high": clear IOC or well-known attack pattern
  - "medium": suspicious but ambiguous
  - "low": possible threat, could be benign

{technique_ref}

RESPONSE FORMAT:
Respond with ONLY a valid JSON array — no explanation, no markdown, no preamble.
Each element must have exactly these fields:
{{
  "threat_description": "brief description of what was detected",
  "technique_id": "T1059.001",
  "tactic": "Execution",
  "confidence": "high",
  "evidence": "exact log line or snippet that triggered this finding"
}}"""


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


class ThreatFinding(BaseModel):
    threat_description: str
    technique_id: str
    technique_name: str
    tactic: str
    confidence: str         
    url: str
    evidence: str


class AnalysisResponse(BaseModel):
    filename: str
    file_size_bytes: int
    chunks_analyzed: int
    findings: list[ThreatFinding]
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


def enrich_finding(raw: dict) -> ThreatFinding | None:
    tid = raw.get("technique_id", "").strip().upper()
    if not tid:
        return None

    technique = mitre_data.get_object_by_attack_id(
        attack_id=tid, stix_type="attack-pattern"
    )
    if technique is None:
        return None

    tactic = raw.get("tactic", "Unknown")
    if hasattr(technique, "kill_chain_phases") and technique.kill_chain_phases:
        for phase in technique.kill_chain_phases:
            if phase.kill_chain_name == "mitre-attack":
                tactic = phase.phase_name.replace("-", " ").title()
                break

    confidence = raw.get("confidence", "medium").lower()
    if confidence not in ("high", "medium", "low"):
        confidence = "medium"

    return ThreatFinding(
        threat_description=raw.get("threat_description", ""),
        technique_id=tid,
        technique_name=technique.name,
        tactic=tactic,
        confidence=confidence,
        url=build_mitre_url(tid),
        evidence=raw.get("evidence", ""),
    )


CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}


def deduplicate_findings(findings: list[ThreatFinding]) -> list[ThreatFinding]:
    best: dict[str, ThreatFinding] = {}
    for f in findings:
        existing = best.get(f.technique_id)
        if existing is None:
            best[f.technique_id] = f
        elif CONFIDENCE_RANK.get(f.confidence, 0) > CONFIDENCE_RANK.get(existing.confidence, 0):
            best[f.technique_id] = f
    return sorted(
        best.values(),
        key=lambda x: (-CONFIDENCE_RANK.get(x.confidence, 0), x.technique_id),
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

    all_findings: list[ThreatFinding] = []
    for i, chunk in enumerate(chunks, start=1):
        raw_results = analyze_chunk(chunk, i, len(chunks))
        for raw in raw_results:
            finding = enrich_finding(raw)
            if finding is not None:
                all_findings.append(finding)

    final_findings = deduplicate_findings(all_findings)

    return AnalysisResponse(
        filename=file.filename or "upload.txt",
        file_size_bytes=len(contents),
        chunks_analyzed=len(chunks),
        findings=final_findings,
        raw_log_preview=text[:500],
    )
