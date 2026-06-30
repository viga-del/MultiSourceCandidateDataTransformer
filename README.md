# Multi-Source Candidate Data Transformer

Merges candidate data from multiple structured and unstructured sources
(Recruiter CSV, ATS JSON, GitHub profile, LinkedIn text/export, Resume
PDF/DOCX, Recruiter notes .txt) into one clean, deduplicated, canonical
JSON profile — with per-field confidence scores and provenance (where
each value came from).

No browser / web server is required — everything runs from a single CLI
command, which is ideal for running straight from VS Code's terminal.

## Pipeline

```
detect → extract → parse → map-to-canonical → merge → confidence
→ provenance → project-to-output → validate → save
```

| Step | Module |
|---|---|
| Detect file type | `app/services/transformation_service.py` |
| Extract raw text/data | `app/extractors/` |
| Parse into fields | `app/parsers/` |
| Map to canonical schema | `app/canonical/canonical_mapper.py` |
| Normalize (dates, phones, emails, skills, names, location) | `app/normalizers/` |
| Merge across sources / resolve conflicts / dedupe | `app/merger/` |
| Confidence scoring | `app/confidence/confidence_calculator.py` |
| Provenance tracking | `app/provenance/provenance_tracker.py` |
| Output projection (default + runtime config) | `app/projection/` |
| Schema validation | `app/validator/` |

## Setup

```bash
cd CandidateDataTransformer
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

## Run (default schema)

Run on the bundled sample inputs (CSV + ATS JSON + recruiter notes):

```bash
python run_cli.py --files input/csv/candidate.csv input/json/candidate.json input/notes/john_notes.txt
```

Or let it auto-discover every file under `input/`:

```bash
python run_cli.py
```

Add a resume: drop a `.pdf` or `.docx` into `input/resumes/` and include it
in `--files` (or just re-run with no `--files`, since auto-discovery picks
it up).

Add GitHub or LinkedIn:

```bash
python run_cli.py --files input/csv/candidate.csv --github johndoe
python run_cli.py --files input/csv/candidate.csv --linkedin-text "paste linkedin profile text here"
```

The merged profile prints to the terminal and is saved to
`output/profiles/<candidate_id>.json`.

## Run with a custom output config (the "required twist")

Reshape the output (select fields, rename, normalize, toggle
confidence/provenance, choose missing-value behavior) **without touching
any code** — just point at a JSON config:

```bash
python run_cli.py --files input/csv/candidate.csv input/json/candidate.json input/notes/john_notes.txt --config app/config/custom_projection_example.json
```

Example config (`app/config/custom_projection_example.json`):

```json
{
  "fields": [
    { "path": "full_name", "type": "string", "required": true },
    { "path": "primary_email", "from": "emails[0]", "type": "string", "required": true },
    { "path": "phone", "from": "phones[0]", "type": "string", "normalize": "E164" },
    { "path": "skills", "from": "skills[].name", "type": "string[]", "normalize": "canonical" }
  ],
  "include_confidence": true,
  "include_provenance": false,
  "on_missing": "null"
}
```

Write your own config file anywhere and pass its path with `--config`.

## CLI flags

| Flag | Description |
|---|---|
| `--files / -f` | Input file paths (PDF, DOCX, CSV, JSON, TXT). Omit to auto-discover everything under `input/`. |
| `--github / -g` | GitHub username to merge in. |
| `--linkedin-text` | Raw LinkedIn profile text to parse and merge in. |
| `--fields` | Restrict default-schema output to specific top-level fields. |
| `--config / -c` | Path to a runtime projection config (overrides `--fields`). |
| `--no-save` | Print only, skip writing to `output/profiles/`. |

## Tests

```bash
python -m pytest tests/ -v
# or, without pytest installed:
python tests/test_pipeline.py
```

Covers: end-to-end run on sample inputs, the custom projection config
path, and the edge case of a malformed/garbage input source (must not
crash the run).

## Design notes / assumptions

- **Merge key**: candidates are matched primarily by normalized email,
  falling back to fuzzy name + phone matching (`app/merger/duplicate_detector.py`).
- **Conflict resolution**: configurable per-field source priority
  (`app/config/source_priority.json`), e.g. Resume/LinkedIn outrank
  free-text recruiter notes for skills.
- **Confidence**: weighted by source priority + number of corroborating
  sources + per-field confidence rules (`app/config/confidence_rules.json`).
- **Robustness**: a missing or malformed source is logged and skipped —
  never crashes the run, never invents data.
- **Out of scope / deliberately left out** given time constraints: a web
  UI (removed in favor of a clean CLI), batch processing of thousands of
  candidates in one process, OAuth-based LinkedIn API access (LinkedIn
  has no public read API — handled via pasted text/export JSON instead).
