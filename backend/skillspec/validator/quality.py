"""
Quality Validation (Layer 2).

Validates quality aspects of a skill specification:
- Forbidden patterns detection
- Decision rules expression parsing
- Output contract schema validation
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml


@dataclass
class PatternViolation:
    """Represents a forbidden pattern violation."""

    path: str
    pattern: str
    matched_text: str
    category: str
    severity: str
    fix_suggestion: str
    line_number: Optional[int] = None

    def __str__(self) -> str:
        loc = f"[{self.path}]"
        if self.line_number:
            loc = f"[{self.path}:{self.line_number}]"
        return (
            f"{loc} [{self.severity.upper()}] {self.category}: "
            f"Found '{self.matched_text}' (pattern: {self.pattern}). "
            f"Fix: {self.fix_suggestion}"
        )


@dataclass
class QualityValidationResult:
    """Result of quality validation."""

    valid: bool
    violations: List[PatternViolation] = field(default_factory=list)
    category_counts: Dict[str, int] = field(default_factory=dict)
    total_errors: int = 0
    total_warnings: int = 0
    total_info: int = 0

    def add_violation(self, violation: PatternViolation) -> None:
        """Add a violation and update counts."""
        self.violations.append(violation)

        # Update category count
        self.category_counts[violation.category] = (
            self.category_counts.get(violation.category, 0) + 1
        )

        # Update severity counts
        if violation.severity == "error":
            self.total_errors += 1
            self.valid = False
        elif violation.severity == "warning":
            self.total_warnings += 1
        elif violation.severity == "info":
            self.total_info += 1


@dataclass
class ForbiddenPattern:
    """A forbidden pattern definition."""

    pattern: str
    category: str
    severity: str
    context: str
    fix: str
    is_regex: bool = False

    def match(self, text: str) -> Optional[str]:
        """
        Check if pattern matches text.

        Returns the matched text if found, None otherwise.
        """
        if self.is_regex:
            match = re.search(self.pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        else:
            # Case-insensitive literal match
            lower_text = text.lower()
            lower_pattern = self.pattern.lower()
            if lower_pattern in lower_text:
                # Find the original case match
                idx = lower_text.find(lower_pattern)
                return text[idx:idx + len(self.pattern)]
        return None


class QualityValidator:
    """
    Validates quality aspects of skill specifications (Layer 2).

    Checks:
    - Forbidden patterns in prose fields
    - Decision rules expression syntax
    - Output contract schema validity
    """

    def __init__(
        self,
        patterns_dir: Optional[Path] = None,
        languages: Optional[List[str]] = None
    ):
        """
        Initialize the quality validator.

        Args:
            patterns_dir: Directory containing pattern YAML files.
            languages: Languages to load patterns for (default: ["en"]).
        """
        self.patterns_dir = patterns_dir
        self.languages = languages or ["en"]
        self._patterns: Optional[List[ForbiddenPattern]] = None
        self._scan_scope: Optional[Dict[str, Any]] = None
        self._ignore_patterns: Optional[List[re.Pattern]] = None

    @property
    def patterns(self) -> List[ForbiddenPattern]:
        """Load and cache forbidden patterns."""
        if self._patterns is None:
            self._patterns = self._load_patterns()
        return self._patterns

    @property
    def scan_scope(self) -> Dict[str, Any]:
        """Load and cache scan scope configuration."""
        if self._scan_scope is None:
            self._scan_scope = self._load_scan_scope()
        return self._scan_scope

    @property
    def ignore_patterns(self) -> List[re.Pattern]:
        """Get compiled ignore patterns."""
        if self._ignore_patterns is None:
            self._ignore_patterns = []
            for item in self.scan_scope.get("ignore_patterns", []):
                try:
                    self._ignore_patterns.append(
                        re.compile(item["pattern"], re.MULTILINE)
                    )
                except re.error:
                    pass  # Skip invalid regex
        return self._ignore_patterns

    def _load_patterns(self) -> List[ForbiddenPattern]:
        """Load forbidden patterns from YAML files."""
        patterns = []

        if not self.patterns_dir:
            return self._get_default_patterns()

        for lang in self.languages:
            file_path = self.patterns_dir / f"forbidden_patterns_{lang}.yaml"
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    for item in data.get("patterns", []):
                        patterns.append(ForbiddenPattern(
                            pattern=item["pattern"],
                            category=item["category"],
                            severity=item.get("severity", "warning"),
                            context=item.get("context", "any"),
                            fix=item.get("fix", "Review and revise"),
                            is_regex=item.get("regex", False)
                        ))

        return patterns or self._get_default_patterns()

    def _get_default_patterns(self) -> List[ForbiddenPattern]:
        """Get default forbidden patterns."""
        return [
            ForbiddenPattern(
                pattern="as needed",
                category="VAGUE_CONDITION",
                severity="error",
                context="instruction",
                fix="Replace with explicit condition"
            ),
            ForbiddenPattern(
                pattern="if appropriate",
                category="VAGUE_CONDITION",
                severity="error",
                context="instruction",
                fix="Define what 'appropriate' means"
            ),
            ForbiddenPattern(
                pattern="try to",
                category="VAGUE_ACTION",
                severity="error",
                context="action",
                fix="Remove 'try to' and state definite action"
            ),
            ForbiddenPattern(
                pattern=r"\bhelp\b",
                category="VAGUE_ACTION",
                severity="error",
                context="action",
                fix="Replace with specific action",
                is_regex=True
            ),
            ForbiddenPattern(
                pattern=r"\bgenerally\b",
                category="VAGUE_DEGREE",
                severity="error",
                context="any",
                fix="Remove or specify exact cases",
                is_regex=True
            ),
            ForbiddenPattern(
                pattern=r"\btypically\b",
                category="VAGUE_DEGREE",
                severity="error",
                context="any",
                fix="Remove or specify exact cases",
                is_regex=True
            ),
            ForbiddenPattern(
                pattern=r"\bmight\b",
                category="HEDGE_WORDS",
                severity="warning",
                context="any",
                fix="State definite outcome",
                is_regex=True
            ),
            ForbiddenPattern(
                pattern=r"\bcould\b",
                category="HEDGE_WORDS",
                severity="warning",
                context="any",
                fix="State definite outcome",
                is_regex=True
            ),
        ]

    def _load_scan_scope(self) -> Dict[str, Any]:
        """Load scan scope configuration."""
        if self.patterns_dir:
            file_path = self.patterns_dir / "scan_scope.yaml"
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)

        # Default scan scope
        return {
            "scanned_fields": [
                {"path": "steps[*].action", "priority": "high"},
                {"path": "skill.purpose", "priority": "high"},
                {"path": "inputs[*].description", "priority": "medium"},
            ],
            "ignored_fields": [
                {"path": "spec_version"},
                {"path": "skill.name"},
                {"path": "skill.version"},
            ],
            "ignore_patterns": [
                {"pattern": "```[\\s\\S]*?```", "type": "regex"},
                {"pattern": "`[^`]+`", "type": "regex"},
            ],
            "thresholds": {
                "max_errors": 0,
                "max_warnings": 10,
            }
        }

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text before scanning for patterns.

        Removes code blocks, inline code, and other technical content.
        """
        result = text
        for pattern in self.ignore_patterns:
            result = pattern.sub("", result)
        return result

    def _get_scannable_fields(
        self,
        spec_data: Dict[str, Any]
    ) -> List[Tuple[str, str]]:
        """
        Extract fields to scan from spec data.

        Returns list of (path, value) tuples.
        """
        fields = []
        ignored_paths = {
            item["path"]
            for item in self.scan_scope.get("ignored_fields", [])
        }

        def extract(data: Any, path: str = "") -> None:
            if path in ignored_paths:
                return

            if isinstance(data, str):
                # Check if path matches any scanned field pattern
                for scanned in self.scan_scope.get("scanned_fields", []):
                    scanned_path = scanned["path"]
                    # Simple pattern matching (supports [*] wildcard)
                    pattern = scanned_path.replace("[*]", r"\[\d+\]")
                    if re.match(f"^{pattern}$", path):
                        fields.append((path, data))
                        break
                else:
                    # If no specific patterns, scan all string fields
                    if not self.scan_scope.get("scanned_fields"):
                        fields.append((path, data))

            elif isinstance(data, dict):
                for key, value in data.items():
                    new_path = f"{path}.{key}" if path else key
                    extract(value, new_path)

            elif isinstance(data, list):
                for i, item in enumerate(data):
                    new_path = f"{path}[{i}]"
                    extract(item, new_path)

        extract(spec_data)
        return fields

    def validate(self, spec_data: Dict[str, Any]) -> QualityValidationResult:
        """
        Validate spec quality.

        Args:
            spec_data: The specification data as a dictionary.

        Returns:
            QualityValidationResult with validation status and violations.
        """
        result = QualityValidationResult(valid=True)

        # Get fields to scan
        fields = self._get_scannable_fields(spec_data)

        # Scan each field for forbidden patterns
        for path, value in fields:
            preprocessed = self._preprocess_text(value)
            for pattern in self.patterns:
                matched = pattern.match(preprocessed)
                if matched:
                    result.add_violation(PatternViolation(
                        path=path,
                        pattern=pattern.pattern,
                        matched_text=matched,
                        category=pattern.category,
                        severity=pattern.severity,
                        fix_suggestion=pattern.fix
                    ))

        # Validate decision rules expressions
        self._validate_decision_rules(spec_data, result)

        # Validate output contract schema
        self._validate_output_contract(spec_data, result)

        return result

    def _validate_decision_rules(
        self,
        spec_data: Dict[str, Any],
        result: QualityValidationResult
    ) -> None:
        """Validate decision rules expressions."""
        decision_rules = spec_data.get("decision_rules", {})

        # Handle both list and dict formats
        rules = []
        if isinstance(decision_rules, list):
            rules = decision_rules
        elif isinstance(decision_rules, dict):
            rules = [
                v for k, v in decision_rules.items()
                if k != "_config" and isinstance(v, dict)
            ]

        for i, rule in enumerate(rules):
            rule_id = rule.get("id", f"rule_{i}")
            when = rule.get("when")

            if when is None:
                result.add_violation(PatternViolation(
                    path=f"decision_rules.{rule_id}.when",
                    pattern="missing",
                    matched_text="<missing>",
                    category="MISSING_CONDITION",
                    severity="error",
                    fix_suggestion="Add 'when' condition to decision rule"
                ))
            elif isinstance(when, str) and when.strip() == "":
                result.add_violation(PatternViolation(
                    path=f"decision_rules.{rule_id}.when",
                    pattern="empty",
                    matched_text="<empty>",
                    category="EMPTY_CONDITION",
                    severity="error",
                    fix_suggestion="Provide non-empty 'when' condition"
                ))

            then = rule.get("then")
            if then is None:
                result.add_violation(PatternViolation(
                    path=f"decision_rules.{rule_id}.then",
                    pattern="missing",
                    matched_text="<missing>",
                    category="MISSING_ACTION",
                    severity="error",
                    fix_suggestion="Add 'then' action to decision rule"
                ))

    def _validate_output_contract(
        self,
        spec_data: Dict[str, Any],
        result: QualityValidationResult
    ) -> None:
        """Validate output contract schema."""
        output_contract = spec_data.get("output_contract", {})
        schema = output_contract.get("schema")

        if schema is None:
            result.add_violation(PatternViolation(
                path="output_contract.schema",
                pattern="missing",
                matched_text="<missing>",
                category="MISSING_SCHEMA",
                severity="error",
                fix_suggestion="Add JSON Schema for output validation"
            ))
        elif not isinstance(schema, dict):
            result.add_violation(PatternViolation(
                path="output_contract.schema",
                pattern="invalid_type",
                matched_text=str(type(schema).__name__),
                category="INVALID_SCHEMA",
                severity="error",
                fix_suggestion="Schema must be a JSON Schema object"
            ))
        elif "type" not in schema and "$ref" not in schema:
            result.add_violation(PatternViolation(
                path="output_contract.schema",
                pattern="missing_type",
                matched_text="<no type>",
                category="INCOMPLETE_SCHEMA",
                severity="warning",
                fix_suggestion="Add 'type' field to schema"
            ))

    def validate_file(self, path: Path) -> QualityValidationResult:
        """
        Validate a YAML file.

        Args:
            path: Path to the spec.yaml file.

        Returns:
            QualityValidationResult with validation status and violations.
        """
        result = QualityValidationResult(valid=True)

        if not path.exists():
            result.add_violation(PatternViolation(
                path=str(path),
                pattern="file_not_found",
                matched_text=str(path),
                category="FILE_ERROR",
                severity="error",
                fix_suggestion="Check the file path"
            ))
            return result

        try:
            with open(path, "r", encoding="utf-8") as f:
                spec_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            result.add_violation(PatternViolation(
                path=str(path),
                pattern="yaml_error",
                matched_text=str(e),
                category="PARSE_ERROR",
                severity="error",
                fix_suggestion="Check YAML syntax"
            ))
            return result

        if spec_data is None:
            result.add_violation(PatternViolation(
                path=str(path),
                pattern="empty_file",
                matched_text="<empty>",
                category="FILE_ERROR",
                severity="error",
                fix_suggestion="Add content to the file"
            ))
            return result

        return self.validate(spec_data)


class SkillMdQualityValidator:
    """
    Relaxed quality validator for SKILL.md files.

    Uses a subset of forbidden patterns appropriate for prose documentation,
    with lower severity levels compared to spec.yaml validation.
    """

    def __init__(self, patterns_dir: Optional[Path] = None):
        """
        Initialize the SKILL.md quality validator.

        Args:
            patterns_dir: Directory containing pattern YAML files.
        """
        self.patterns_dir = patterns_dir
        self._patterns: Optional[List[ForbiddenPattern]] = None

    @property
    def patterns(self) -> List[ForbiddenPattern]:
        """Load and cache relaxed forbidden patterns."""
        if self._patterns is None:
            self._patterns = self._load_relaxed_patterns()
        return self._patterns

    def _load_relaxed_patterns(self) -> List[ForbiddenPattern]:
        """Load relaxed patterns for SKILL.md validation."""
        # Only the most critical patterns for documentation
        return [
            # Placeholder patterns (errors in docs)
            ForbiddenPattern(
                pattern="TODO",
                category="INCOMPLETE_CONTENT",
                severity="error",
                context="any",
                fix="Complete the TODO item"
            ),
            ForbiddenPattern(
                pattern="TBD",
                category="INCOMPLETE_CONTENT",
                severity="error",
                context="any",
                fix="Determine and specify the content"
            ),
            ForbiddenPattern(
                pattern="FIXME",
                category="INCOMPLETE_CONTENT",
                severity="error",
                context="any",
                fix="Fix the issue before publishing"
            ),
            # Vague language (warnings in docs, not errors)
            ForbiddenPattern(
                pattern="as needed",
                category="VAGUE_LANGUAGE",
                severity="warning",
                context="instruction",
                fix="Consider being more specific"
            ),
            ForbiddenPattern(
                pattern="if appropriate",
                category="VAGUE_LANGUAGE",
                severity="warning",
                context="instruction",
                fix="Consider defining criteria"
            ),
            # Empty sections
            ForbiddenPattern(
                pattern=r"##\s+\w+\s*\n\s*\n##",
                category="EMPTY_SECTION",
                severity="warning",
                context="structure",
                fix="Add content to the section",
                is_regex=True
            ),
        ]

    def validate(self, content: str) -> QualityValidationResult:
        """
        Validate SKILL.md content quality.

        Args:
            content: The SKILL.md content as a string.

        Returns:
            QualityValidationResult with validation status and violations.
        """
        result = QualityValidationResult(valid=True)

        # Skip code blocks for pattern matching
        preprocessed = self._preprocess_markdown(content)

        # Check each pattern
        for pattern in self.patterns:
            matched = pattern.match(preprocessed)
            if matched:
                # Find line number
                line_num = self._find_line_number(content, matched)
                result.add_violation(PatternViolation(
                    path="SKILL.md",
                    pattern=pattern.pattern,
                    matched_text=matched,
                    category=pattern.category,
                    severity=pattern.severity,
                    fix_suggestion=pattern.fix,
                    line_number=line_num
                ))

        return result

    def _preprocess_markdown(self, content: str) -> str:
        """Remove code blocks and inline code from markdown."""
        # Remove fenced code blocks
        result = re.sub(r'```[\s\S]*?```', '', content)
        # Remove inline code
        result = re.sub(r'`[^`]+`', '', result)
        return result

    def _find_line_number(self, content: str, match_text: str) -> Optional[int]:
        """Find the line number where the match occurs."""
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if match_text.lower() in line.lower():
                return i
        return None

    def validate_file(self, path: Path) -> QualityValidationResult:
        """
        Validate a SKILL.md file.

        Args:
            path: Path to the SKILL.md file.

        Returns:
            QualityValidationResult with validation status and violations.
        """
        result = QualityValidationResult(valid=True)

        if not path.exists():
            result.add_violation(PatternViolation(
                path=str(path),
                pattern="file_not_found",
                matched_text=str(path),
                category="FILE_ERROR",
                severity="error",
                fix_suggestion="Check the file path"
            ))
            return result

        content = path.read_text(encoding="utf-8")
        return self.validate(content)
