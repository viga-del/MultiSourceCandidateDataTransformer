"""
tests/test_pipeline.py
=======================
A few focused tests covering:
  1. End-to-end run on the provided sample inputs -> schema-valid default output.
  2. Runtime custom projection config -> correctly selected/renamed/normalized output.
  3. Edge case: a malformed/garbage source must not crash the run.

Run with:
    python -m pytest tests/ -v
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.transformation_service import TransformationService

SAMPLE_FILES = [
    "input/csv/candidate.csv",
    "input/json/candidate.json",
    "input/notes/john_notes.txt",
]


def test_default_pipeline_end_to_end():
    service = TransformationService()
    result = service.transform_from_files(file_paths=SAMPLE_FILES, save_output=False)

    assert result["candidate_id"]
    assert result["full_name"] == "John Doe"
    assert "john@gmail.com" in result["emails"]
    assert result["phones"][0].startswith("+91")
    assert any(s["name"].lower() == "java" for s in result["skills"])
    assert 0.0 <= result["overall_confidence"] <= 1.0
    assert len(result["provenance"]) > 0


def test_custom_projection_config():
    config_path = "app/config/custom_projection_example.json"
    with open(config_path) as f:
        config = json.load(f)

    service = TransformationService()
    result = service.transform_from_files(
        file_paths=SAMPLE_FILES, projection_config=config, save_output=False
    )

    # Only the configured fields (+ confidence) should be present
    assert set(result.keys()) == {"full_name", "primary_email", "phone", "skills", "overall_confidence"}
    assert result["primary_email"] == "john@gmail.com"
    assert result["phone"].startswith("+91")
    assert isinstance(result["skills"], list)


def test_garbage_source_does_not_crash():
    """A malformed input file must be skipped, not crash the pipeline,
    as long as at least one valid source is present."""
    garbage_path = "tests/_garbage.json"
    with open(garbage_path, "w") as f:
        f.write("this is not valid json {{{")

    try:
        service = TransformationService()
        result = service.transform_from_files(
            file_paths=[garbage_path, "input/csv/candidate.csv"], save_output=False
        )
        assert result["full_name"] == "John Doe"
    finally:
        os.remove(garbage_path)


def test_no_sources_raises():
    service = TransformationService()
    try:
        service.transform_from_files(file_paths=[], save_output=False)
        assert False, "Expected ValueError for no sources"
    except ValueError:
        pass


if __name__ == "__main__":
    test_default_pipeline_end_to_end()
    test_custom_projection_config()
    test_garbage_source_does_not_crash()
    test_no_sources_raises()
    print("All tests passed.")
