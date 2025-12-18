"""
Schema Validation (Layer 1).

Validates the structure and required fields of a skill specification.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema
from pydantic import ValidationError

from ..models import SkillSpec


@dataclass
class SchemaError:
    """Represents a schema validation error."""

    path: str
    message: str
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        result = f"[{self.path}] {self.message}"
        if self.suggestion:
            result += f" (Suggestion: {self.suggestion})"
        return result


@dataclass
class SchemaValidationResult:
    """Result of schema validation."""

    valid: bool
    errors: List[SchemaError] = field(default_factory=list)
    warnings: List[SchemaError] = field(default_factory=list)

    def add_error(
        self,
        path: str,
        message: str,
        suggestion: Optional[str] = None
    ) -> None:
        """Add a validation error."""
        self.errors.append(SchemaError(path, message, suggestion))
        self.valid = False

    def add_warning(
        self,
        path: str,
        message: str,
        suggestion: Optional[str] = None
    ) -> None:
        """Add a validation warning."""
        self.warnings.append(SchemaError(path, message, suggestion))


# Required sections according to Section Taxonomy v1.0
CORE_SECTIONS = [
    "skill",
    "inputs",
    "preconditions",
    "non_goals",
    "decision_rules",
    "steps",
    "output_contract",
    "failure_modes",
]

COVERAGE_SECTIONS = [
    "edge_cases",
]

CONTEXT_SECTIONS = [
    "context",
]

REQUIRED_SECTIONS = CORE_SECTIONS + COVERAGE_SECTIONS

# Suggestions for common errors
ERROR_SUGGESTIONS = {
    "skill": "Add a 'skill' section with name, version, purpose, and owner",
    "inputs": "Add an 'inputs' section with at least one input definition",
    "preconditions": "Add a 'preconditions' section listing prerequisites",
    "non_goals": "Add a 'non_goals' section stating what the skill does NOT do",
    "decision_rules": "Add 'decision_rules' section with explicit conditions",
    "steps": "Add a 'steps' section with execution flow",
    "output_contract": "Add 'output_contract' with format and schema",
    "failure_modes": "Add 'failure_modes' section with error definitions",
    "edge_cases": "Add 'edge_cases' section covering boundary conditions",
}


class SchemaValidator:
    """
    Validates skill specification schema (Layer 1).

    Checks:
    - All required sections are present
    - Field types are correct
    - Required fields are non-empty
    """

    def __init__(self, schema_path: Optional[Path] = None):
        """
        Initialize the schema validator.

        Args:
            schema_path: Path to JSON Schema file. If None, uses default.
        """
        self.schema_path = schema_path
        self._schema: Optional[Dict[str, Any]] = None

    @property
    def schema(self) -> Dict[str, Any]:
        """Load and cache the JSON Schema."""
        if self._schema is None:
            if self.schema_path and self.schema_path.exists():
                with open(self.schema_path, "r", encoding="utf-8") as f:
                    self._schema = json.load(f)
            else:
                # Use a minimal inline schema if file not found
                self._schema = self._get_default_schema()
        return self._schema

    def _get_default_schema(self) -> Dict[str, Any]:
        """Get the default minimal schema."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": REQUIRED_SECTIONS + ["spec_version"],
        }

    def validate(self, spec_data: Dict[str, Any]) -> SchemaValidationResult:
        """
        Validate a spec against the schema.

        Args:
            spec_data: The specification data as a dictionary.

        Returns:
            SchemaValidationResult with validation status and errors.
        """
        result = SchemaValidationResult(valid=True)

        # Check required sections
        self._check_required_sections(spec_data, result)

        # Check spec_version
        self._check_spec_version(spec_data, result)

        # Try to parse with Pydantic for detailed validation
        if result.valid:
            self._validate_with_pydantic(spec_data, result)

        # Optionally validate with JSON Schema
        if result.valid and self.schema_path:
            self._validate_with_jsonschema(spec_data, result)

        return result

    def _check_required_sections(
        self,
        spec_data: Dict[str, Any],
        result: SchemaValidationResult
    ) -> None:
        """Check that all required sections are present."""
        for section in REQUIRED_SECTIONS:
            if section not in spec_data:
                result.add_error(
                    path=section,
                    message=f"Missing required section: {section}",
                    suggestion=ERROR_SUGGESTIONS.get(section)
                )
            elif spec_data[section] is None:
                result.add_error(
                    path=section,
                    message=f"Section '{section}' is null",
                    suggestion=f"Provide valid content for '{section}'"
                )
            elif isinstance(spec_data[section], list) and len(spec_data[section]) == 0:
                result.add_error(
                    path=section,
                    message=f"Section '{section}' is empty",
                    suggestion=f"Add at least one item to '{section}'"
                )

    def _check_spec_version(
        self,
        spec_data: Dict[str, Any],
        result: SchemaValidationResult
    ) -> None:
        """Check spec_version field."""
        valid_versions = {"skill-spec/1.0", "skill-spec/1.1"}
        if "spec_version" not in spec_data:
            result.add_error(
                path="spec_version",
                message="Missing required field: spec_version",
                suggestion="Add 'spec_version: \"skill-spec/1.1\"'"
            )
        elif spec_data["spec_version"] not in valid_versions:
            result.add_warning(
                path="spec_version",
                message=f"Unknown spec version: {spec_data['spec_version']}",
                suggestion="Use 'skill-spec/1.0' or 'skill-spec/1.1'"
            )

    def _validate_with_pydantic(
        self,
        spec_data: Dict[str, Any],
        result: SchemaValidationResult
    ) -> None:
        """Validate using Pydantic models for detailed error messages."""
        try:
            SkillSpec.model_validate(spec_data)
        except ValidationError as e:
            for error in e.errors():
                path = ".".join(str(loc) for loc in error["loc"])
                result.add_error(
                    path=path,
                    message=error["msg"],
                    suggestion=self._get_suggestion_for_error(error)
                )

    def _validate_with_jsonschema(
        self,
        spec_data: Dict[str, Any],
        result: SchemaValidationResult
    ) -> None:
        """Validate using JSON Schema."""
        try:
            jsonschema.validate(spec_data, self.schema)
        except jsonschema.ValidationError as e:
            path = ".".join(str(p) for p in e.absolute_path) or "root"
            result.add_error(
                path=path,
                message=e.message,
                suggestion=None
            )
        except jsonschema.SchemaError as e:
            result.add_error(
                path="schema",
                message=f"Invalid schema: {e.message}",
                suggestion="Check the JSON Schema file for errors"
            )

    def _get_suggestion_for_error(self, error: Dict[str, Any]) -> Optional[str]:
        """Generate a suggestion for a Pydantic validation error."""
        error_type = error.get("type", "")
        loc = error.get("loc", [])

        if error_type == "missing":
            field = loc[-1] if loc else "unknown"
            return f"Add the required field '{field}'"
        elif error_type == "string_pattern_mismatch":
            return "Check the format matches the required pattern"
        elif error_type == "string_too_short":
            return "Provide a longer value"
        elif error_type == "list_type":
            return "This field should be a list"

        return None

    def validate_file(self, path: Path) -> SchemaValidationResult:
        """
        Validate a YAML file.

        Args:
            path: Path to the spec.yaml file.

        Returns:
            SchemaValidationResult with validation status and errors.
        """
        import yaml

        result = SchemaValidationResult(valid=True)

        if not path.exists():
            result.add_error(
                path=str(path),
                message="File not found",
                suggestion="Check the file path"
            )
            return result

        try:
            with open(path, "r", encoding="utf-8") as f:
                spec_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            result.add_error(
                path=str(path),
                message=f"YAML parse error: {e}",
                suggestion="Check YAML syntax"
            )
            return result

        if spec_data is None:
            result.add_error(
                path=str(path),
                message="File is empty",
                suggestion="Add spec content to the file"
            )
            return result

        return self.validate(spec_data)
