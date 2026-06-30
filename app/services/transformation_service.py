# app/services/transformation_service.py
#
# The Transformation Service is the MAIN ORCHESTRATOR.
# It calls every module in the correct order:
#
# 1. Source Detection  → identify file type
# 2. Extraction        → read raw data
# 3. Parsing           → extract structured fields from raw data
# 4. Canonical Mapping → convert to standard schema
# 5. Merge             → combine all sources
# 6. Confidence        → calculate scores
# 7. Provenance        → track data origins
# 8. Projection        → select output fields
# 9. Validation        → verify the final JSON
# 10. Save             → write to output/profiles/
#
# This service is the only file that imports from ALL modules.
# The API layer (FastAPI) only imports this service.

import os
import json
from typing import List, Optional, Dict, Any
from dataclasses import asdict

# ── Extractors ────────────────────────────────────────────────────────
from app.extractors.pdf_extractor      import extract_text_from_pdf
from app.extractors.docx_extractor     import extract_text_from_docx
from app.extractors.csv_extractor      import extract_from_csv
from app.extractors.json_extractor     import extract_from_json
from app.extractors.github_extractor   import extract_from_github
from app.extractors.linkedin_extractor import extract_from_linkedin_json, extract_from_linkedin_text
from app.extractors.notes_extractor    import extract_from_notes

# ── Parsers ───────────────────────────────────────────────────────────
from app.parsers.resume_parser   import parse_resume
from app.parsers.github_parser   import parse_github
from app.parsers.linkedin_parser import parse_linkedin
from app.parsers.notes_parser    import parse_notes

# ── Canonical Mapper ──────────────────────────────────────────────────
from app.canonical.canonical_mapper import (
    map_resume_to_canonical,
    map_csv_to_canonical,
    map_json_to_canonical,
    map_github_to_canonical,
    map_linkedin_to_canonical,
    map_notes_to_canonical,
)

# ── Merge Engine ──────────────────────────────────────────────────────
from app.merger.merge_engine import merge_canonical_sources

# ── Confidence Calculator ─────────────────────────────────────────────
from app.confidence.confidence_calculator import calculate_all_confidences

# ── Provenance Tracker ────────────────────────────────────────────────
from app.provenance.provenance_tracker import build_provenance

# ── Projection Engine ─────────────────────────────────────────────────
from app.projection.projection_engine import project_profile
from app.projection.config_projection_engine import project_with_config

# ── Validator ─────────────────────────────────────────────────────────
from app.validator.json_validator import validate_and_collect_all_errors, validate_custom_projection

from app.utils.constants import EXT_PDF, EXT_DOCX, EXT_CSV, EXT_JSON, EXT_TXT
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Output directory for saved profiles
OUTPUT_DIR = os.path.join("output", "profiles")
os.makedirs(OUTPUT_DIR, exist_ok=True)


class TransformationService:
    """
    Main orchestration service for the candidate data transformation pipeline.

    Usage:
        service = TransformationService()

        # Process files from disk
        result = service.transform_from_files(
            file_paths=["input/resumes/john.pdf", "input/csv/candidates.csv"],
            github_username="johndoe"
        )

        # The result is the final candidate JSON
        print(result)
    """

    def transform_from_files(
        self,
        file_paths: List[str],
        github_username: Optional[str] = None,
        linkedin_text: Optional[str] = None,
        projection_fields: Optional[List[str]] = None,
        projection_config: Optional[Dict[str, Any]] = None,
        save_output: bool = True,
    ) -> Dict[str, Any]:
        """
        Run the complete transformation pipeline on a set of input files.

        Parameters:
            file_paths        : List of file paths (PDF, DOCX, CSV, JSON, TXT)
            github_username   : Optional GitHub username to fetch profile from API
            linkedin_text     : Optional plain text of a LinkedIn profile
            projection_fields : Optional list of fields to include in output
                               (overrides projection.json config)
            save_output       : Whether to save the result JSON to output/profiles/

        Returns:
            Dict: The final canonical candidate profile JSON

        Raises:
            ValueError: If no files or sources are provided
        """
        logger.info("=" * 60)
        logger.info("Starting transformation pipeline")
        logger.info(f"Files: {file_paths}")
        logger.info(f"GitHub: {github_username}")
        logger.info("=" * 60)

        if not file_paths and not github_username and not linkedin_text:
            raise ValueError("At least one input source must be provided")

        canonical_list = []   # All canonical dicts from all sources

        # ── Step 1+2+3+4: Extract → Parse → Map for each file ─────────
        for file_path in file_paths:
            canon = self._process_file(file_path)
            if canon:
                canonical_list.append(canon)

        # ── GitHub ────────────────────────────────────────────────────
        if github_username:
            canon = self._process_github(github_username)
            if canon:
                canonical_list.append(canon)

        # ── LinkedIn text ─────────────────────────────────────────────
        if linkedin_text:
            canon = self._process_linkedin_text(linkedin_text)
            if canon:
                canonical_list.append(canon)

        if not canonical_list:
            logger.error("No data could be extracted from any source")
            raise ValueError("No data could be extracted from the provided sources")

        logger.info(f"Successfully processed {len(canonical_list)} source(s)")

        # ── Step 5: Merge all canonical sources ───────────────────────
        profile = merge_canonical_sources(canonical_list)

        # ── Step 6: Calculate confidence scores ───────────────────────
        profile = calculate_all_confidences(profile)

        # ── Step 7: Build provenance records ──────────────────────────
        profile = build_provenance(profile, canonical_list)

        # ── Step 8: Project (select output fields) ────────────────────
        if projection_config:
            output_dict = project_with_config(profile, projection_config)
        else:
            output_dict = project_profile(profile, projection_fields)

        # ── Step 9: Validate ──────────────────────────────────────────
        if projection_config:
            is_valid, errors = validate_custom_projection(output_dict, projection_config)
        else:
            is_valid, errors = validate_and_collect_all_errors(output_dict)
        if not is_valid:
            logger.warning(f"Output has {len(errors)} validation issue(s):")
            for err in errors:
                logger.warning(f"  • {err}")
            # We still return the output — just log the issues
            # In strict mode you might raise an exception here

        # ── Step 10: Save to disk ─────────────────────────────────────
        if save_output:
            self._save_profile(output_dict)

        logger.info("=" * 60)
        logger.info(f"Pipeline complete. Candidate: {output_dict.get('full_name')}")
        logger.info(f"Overall confidence: {output_dict.get('overall_confidence')}")
        logger.info("=" * 60)

        return output_dict

    # ──────────────────────────────────────────────────────────────────
    # Private helper methods
    # ──────────────────────────────────────────────────────────────────

    def _process_file(self, file_path: str) -> Optional[Dict]:
        """
        Detect file type, extract, parse, and map to canonical format.

        Parameters:
            file_path (str): Path to the input file

        Returns:
            Dict: Canonical dict, or None if processing failed
        """
        # Get the file extension in lowercase
        # os.path.splitext("file.pdf") → ("file", ".pdf")
        _, ext = os.path.splitext(file_path.lower())

        logger.info(f"Processing file: {file_path} (type: {ext})")

        try:
            if ext == EXT_PDF:
                # PDF: extract text → parse as resume → map to canonical
                raw_text = extract_text_from_pdf(file_path)
                parsed   = parse_resume(raw_text)
                return map_resume_to_canonical(parsed)

            elif ext == EXT_DOCX:
                # DOCX: extract text → parse as resume → map to canonical
                raw_text = extract_text_from_docx(file_path)
                parsed   = parse_resume(raw_text)
                return map_resume_to_canonical(parsed)

            elif ext == EXT_CSV:
                # CSV: extract rows → map first row to canonical
                # (In a real system you'd handle multiple rows as multiple candidates)
                rows = extract_from_csv(file_path)
                if rows:
                    # Process first candidate row
                    return map_csv_to_canonical(rows[0])

            elif ext == EXT_JSON:
                # Check if it's a LinkedIn export or ATS JSON
                raw_data = extract_from_json(file_path)
                if _is_linkedin_export(raw_data):
                    parsed = parse_linkedin(raw_data)
                    return map_linkedin_to_canonical(parsed)
                else:
                    return map_json_to_canonical(raw_data)

            elif ext == EXT_TXT:
                # TXT: extract text → parse as recruiter notes
                raw_text = extract_from_notes(file_path)
                parsed   = parse_notes(raw_text)
                return map_notes_to_canonical(parsed)

            else:
                logger.warning(f"Unsupported file type: {ext} for file {file_path}")
                return None

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
            return None

    def _process_github(self, username: str) -> Optional[Dict]:
        """Extract and map GitHub profile data."""
        try:
            raw_data = extract_from_github(username)
            if raw_data:
                parsed = parse_github(raw_data)
                return map_github_to_canonical(parsed)
        except Exception as e:
            logger.error(f"Error processing GitHub for {username}: {e}")
        return None

    def _process_linkedin_text(self, text: str) -> Optional[Dict]:
        """Parse and map a LinkedIn plain text profile."""
        try:
            raw_data = extract_from_linkedin_text(text)
            parsed   = parse_linkedin(raw_data)
            return map_linkedin_to_canonical(parsed)
        except Exception as e:
            logger.error(f"Error processing LinkedIn text: {e}")
        return None

    def _save_profile(self, output_dict: Dict) -> str:
        """
        Save the final profile JSON to output/profiles/.

        Filename: {candidate_id}.json
        Example:  output/profiles/C-4a8f2b1e.json

        Parameters:
            output_dict (Dict): The final output JSON

        Returns:
            str: Path where the file was saved
        """
        candidate_id = output_dict.get("candidate_id", "unknown")
        file_name = f"{candidate_id}.json"
        file_path = os.path.join(OUTPUT_DIR, file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            # json.dump() writes the dict as formatted JSON
            # indent=2 makes it human-readable with 2-space indentation
            # ensure_ascii=False allows Unicode characters (accented names etc.)
            json.dump(output_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"Profile saved to: {file_path}")
        return file_path


def _is_linkedin_export(data: Dict) -> bool:
    """
    Heuristic to detect if a JSON file is a LinkedIn export.
    LinkedIn exports have characteristic field names.

    Parameters:
        data (Dict): Loaded JSON data

    Returns:
        bool: True if this looks like a LinkedIn export
    """
    linkedin_indicators = ["firstName", "lastName", "headline", "publicProfileUrl", "positions"]
    return any(key in data for key in linkedin_indicators)
