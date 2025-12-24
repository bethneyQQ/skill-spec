"""
Pydantic models for Skill-Spec specification.

This module defines the data models for skill specifications following
the Section Taxonomy v1.0:
- Core Sections (8 required): skill, inputs, preconditions, non_goals,
  decision_rules, steps, output_contract, failure_modes
- Coverage Sections (1 required): edge_cases
- Context Sections (1 optional): context
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


# Enums for constrained string fields

class ContentLanguage(str, Enum):
    """Supported content languages."""
    EN = "en"
    ZH = "zh"
    AUTO = "auto"


class MixedLanguageStrategy(str, Enum):
    """Strategy for handling mixed language content."""
    UNION = "union"
    SEGMENT_DETECT = "segment_detect"
    PRIMARY = "primary"


class InputType(str, Enum):
    """Supported input data types."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


class DomainType(str, Enum):
    """Domain types for coverage analysis."""
    ENUM = "enum"
    RANGE = "range"
    PATTERN_SET = "pattern_set"
    BOOLEAN = "boolean"
    ANY = "any"


class MatchStrategy(str, Enum):
    """Strategy for matching decision rules."""
    FIRST_MATCH = "first_match"
    PRIORITY = "priority"
    ALL_MATCH = "all_match"


class ConflictResolution(str, Enum):
    """How to handle multiple rule matches."""
    ERROR = "error"
    WARN = "warn"
    FIRST_WINS = "first_wins"


class OutputFormat(str, Enum):
    """Supported output formats."""
    JSON = "json"
    TEXT = "text"
    MARKDOWN = "markdown"
    YAML = "yaml"
    BINARY = "binary"


class RuleStatus(str, Enum):
    """Status values for rule outcomes."""
    SUCCESS = "success"
    ERROR = "error"
    SKIP = "skip"
    DELEGATE = "delegate"


class LogLevel(str, Enum):
    """Log levels for rule actions."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


# Pattern constants

KEBAB_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
UPPER_SNAKE_CASE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


# Model definitions

class ProgressiveDisclosure(BaseModel):
    """
    v1.2: Token budget configuration for progressive disclosure (agentskills.io pattern).

    Defines token limits for different disclosure levels:
    - metadata_tokens: ~100 tokens for metadata loaded at startup
    - instructions_tokens: <5000 tokens for main instructions
    - max_lines: <500 lines for SKILL.md file
    """

    metadata_tokens: int = Field(
        default=100,
        ge=50,
        le=200,
        description="Target tokens for metadata section (~100 tokens recommended)"
    )
    instructions_tokens: int = Field(
        default=2000,
        ge=500,
        le=5000,
        description="Target tokens for instructions section (<5000 tokens recommended)"
    )
    max_lines: int = Field(
        default=500,
        ge=100,
        le=1000,
        description="Maximum lines for main SKILL.md file (<500 lines recommended)"
    )

    class Config:
        extra = "forbid"


class MetaConfig(BaseModel):
    """Meta configuration for the spec."""

    content_language: ContentLanguage = Field(
        default=ContentLanguage.EN,
        description="Primary content language"
    )
    mixed_language_strategy: MixedLanguageStrategy = Field(
        default=MixedLanguageStrategy.UNION,
        description="Strategy for mixed language validation"
    )
    # v1.1 fields
    format: Optional[Literal["full", "minimal"]] = Field(
        default="full",
        description="v1.1: Spec format - full or minimal"
    )
    token_budget: Optional[int] = Field(
        default=500,
        ge=50,
        le=2000,
        description="v1.1: Target word count for generated SKILL.md"
    )
    # v1.2 fields
    agentskills_compat: bool = Field(
        default=False,
        description="v1.2: Enable agentskills.io compatibility mode"
    )
    progressive_disclosure: Optional[ProgressiveDisclosure] = Field(
        default=None,
        description="v1.2: Token budget configuration for progressive disclosure"
    )

    class Config:
        extra = "forbid"


class SkillMetadata(BaseModel):
    """
    Core skill metadata (Section 1).

    Defines the identity and ownership of a skill.
    v1.2 adds agentskills.io compatibility fields.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Kebab-case skill name (1-64 chars, agentskills.io compliant)",
        examples=["extract-api-contract", "code-review-assistant"]
    )
    version: str = Field(
        ...,
        description="Semantic version (MAJOR.MINOR.PATCH)"
    )
    purpose: str = Field(
        ...,
        min_length=10,
        max_length=1024,
        description="Single sentence purpose statement. Maps to 'description' in agentskills.io (1-1024 chars)"
    )
    owner: str = Field(
        ...,
        min_length=1,
        description="Team or individual responsible"
    )
    # v1.1 fields
    category: Optional[str] = Field(
        default=None,
        description="v1.1: Skill category for classification"
    )
    complexity: Optional[str] = Field(
        default="standard",
        description="v1.1: Complexity level (low, standard, advanced)"
    )
    tools_required: Optional[List[str]] = Field(
        default=None,
        description="v1.1: Tools/capabilities this skill needs"
    )
    personas: Optional[List[str]] = Field(
        default=None,
        description="v1.1: Roles that benefit from this skill"
    )
    # v1.2 agentskills.io fields
    license: Optional[str] = Field(
        default=None,
        description="v1.2 (agentskills.io): SPDX license identifier or reference to LICENSE file"
    )
    compatibility: Optional[str] = Field(
        default=None,
        max_length=500,
        description="v1.2 (agentskills.io): Environment requirements (max 500 chars)"
    )
    allowed_tools: Optional[List[str]] = Field(
        default=None,
        description="v1.2 (agentskills.io): Pre-approved tools for execution (experimental)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="v1.2 (agentskills.io): Custom key-value properties beyond the spec"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate skill name follows kebab-case pattern and length constraints."""
        if not KEBAB_CASE_PATTERN.match(v):
            raise ValueError(
                f"Skill name must be kebab-case (e.g., 'extract-api-contract'), got: {v}"
            )
        if len(v) > 64:
            raise ValueError(
                f"Skill name must be 1-64 characters (agentskills.io), got: {len(v)}"
            )
        return v

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version follows semantic versioning."""
        if not SEMVER_PATTERN.match(v):
            raise ValueError(
                f"Version must follow semver (e.g., '1.0.0'), got: {v}"
            )
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        """Validate category is one of the allowed values."""
        if v is None:
            return v
        allowed = ["documentation", "analysis", "generation", "transformation",
                   "validation", "orchestration", "other"]
        if v not in allowed:
            raise ValueError(f"Category must be one of {allowed}, got: {v}")
        return v

    @field_validator("complexity")
    @classmethod
    def validate_complexity(cls, v: Optional[str]) -> Optional[str]:
        """Validate complexity is one of the allowed values."""
        if v is None:
            return v
        allowed = ["low", "standard", "advanced"]
        if v not in allowed:
            raise ValueError(f"Complexity must be one of {allowed}, got: {v}")
        return v

    class Config:
        extra = "forbid"


class LengthConstraint(BaseModel):
    """Extended length constraint with mode support."""

    value: int = Field(..., ge=1)
    mode: Literal["chars", "tokens", "info_units"] = Field(default="chars")
    override_reason: Optional[str] = None


class InputDomain(BaseModel):
    """
    Domain specification for coverage analysis.

    Defines the valid input space for an input parameter.
    """

    type: DomainType = Field(
        ...,
        description="Domain type for coverage calculation"
    )
    values: Optional[List[Any]] = Field(
        default=None,
        description="Enum values (for type: enum)"
    )
    min: Optional[float] = Field(
        default=None,
        description="Minimum value (for type: range)"
    )
    max: Optional[float] = Field(
        default=None,
        description="Maximum value (for type: range)"
    )
    patterns: Optional[List[str]] = Field(
        default=None,
        description="Pattern set (for type: pattern_set)"
    )

    @model_validator(mode="after")
    def validate_domain_fields(self) -> "InputDomain":
        """Validate domain fields match the domain type."""
        if self.type == DomainType.ENUM and not self.values:
            raise ValueError("Enum domain requires 'values' field")
        if self.type == DomainType.RANGE and (self.min is None or self.max is None):
            raise ValueError("Range domain requires 'min' and 'max' fields")
        if self.type == DomainType.PATTERN_SET and not self.patterns:
            raise ValueError("Pattern set domain requires 'patterns' field")
        return self


class InputSpec(BaseModel):
    """
    Input specification with domain support (Section 2).

    Defines a single input parameter with its type, constraints, and domain.
    """

    name: str = Field(
        ...,
        description="Input parameter name (snake_case)"
    )
    type: InputType = Field(
        ...,
        description="Data type"
    )
    required: bool = Field(
        ...,
        description="Whether this input is required"
    )
    constraints: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        default=None,
        description="Validation constraints"
    )
    domain: Optional[InputDomain] = Field(
        default=None,
        description="Domain specification for coverage analysis"
    )
    description: Optional[str] = Field(
        default=None,
        description="Semantic definition of this input"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Data classification tags"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate input name follows snake_case pattern."""
        if not SNAKE_CASE_PATTERN.match(v):
            raise ValueError(
                f"Input name must be snake_case (e.g., 'user_input'), got: {v}"
            )
        return v

    class Config:
        extra = "forbid"


class RuleAction(BaseModel):
    """Action to take when a decision rule matches."""

    status: Optional[RuleStatus] = None
    code: Optional[str] = Field(
        default=None,
        description="Error or result code"
    )
    action: Optional[str] = Field(
        default=None,
        description="Action to execute"
    )
    path: Optional[str] = Field(
        default=None,
        description="Execution path to follow"
    )
    log: Optional[LogLevel] = None

    class Config:
        extra = "allow"  # Allow additional fields for flexibility


class DecisionRule(BaseModel):
    """
    Individual decision rule.

    Defines a condition-action pair with priority support.
    When used as key-value pairs in decision_rules, the key serves as the id.
    """

    id: Optional[str] = Field(
        default=None,
        description="Unique rule identifier. Auto-generated if not provided."
    )
    priority: int = Field(
        default=0,
        ge=0,
        description="Rule priority (higher = checked first)"
    )
    is_default: bool = Field(
        default=False,
        description="Whether this is the default/fallback rule"
    )
    when: Union[str, bool, Dict[str, Any]] = Field(
        ...,
        description="Condition expression (simple syntax or JSON Logic)"
    )
    then: Dict[str, Any] = Field(
        ...,
        description="Action to take when condition matches"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate rule ID follows snake_case pattern if provided."""
        if v is None:
            return v
        if not SNAKE_CASE_PATTERN.match(v):
            raise ValueError(
                f"Rule ID must be snake_case (e.g., 'rule_validation'), got: {v}"
            )
        return v

    class Config:
        extra = "forbid"


class DecisionRulesConfig(BaseModel):
    """Configuration for decision rule matching."""

    match_strategy: MatchStrategy = Field(
        default=MatchStrategy.FIRST_MATCH,
        description="How to select matching rules"
    )
    conflict_resolution: ConflictResolution = Field(
        default=ConflictResolution.ERROR,
        description="How to handle multiple matches"
    )

    class Config:
        extra = "forbid"


class DecisionRules(BaseModel):
    """
    Decision rules with configuration (Section 5).

    Contains the configuration and list of decision rules.
    """

    config: DecisionRulesConfig = Field(
        default_factory=DecisionRulesConfig,
        alias="_config"
    )
    rules: List[DecisionRule] = Field(
        default_factory=list,
        description="List of decision rules"
    )

    @model_validator(mode="before")
    @classmethod
    def extract_rules(cls, values: Any) -> Any:
        """
        Extract rules from the raw decision_rules dict/list.

        Supports three formats:
        1. Canonical format: {"_config": {...}, "rules": [...]}
        2. Legacy key-value format: {"_config": {...}, "rule_id": {...}, ...}
        3. Legacy list format: [{...}, {...}]

        Auto-generates rule IDs for rules that don't have explicit ids.
        """
        def ensure_rule_ids(rules_list: list, start_index: int = 0) -> list:
            """Ensure each rule has an id, auto-generating if needed."""
            result = []
            for i, rule in enumerate(rules_list):
                if isinstance(rule, dict) and "id" not in rule:
                    rule = {**rule, "id": f"rule_{start_index + i}"}
                result.append(rule)
            return result

        if isinstance(values, dict):
            config = values.get("_config", {})

            # Format 1: Canonical format with rules key
            if "rules" in values:
                rules = values["rules"]
                if isinstance(rules, list):
                    rules = ensure_rule_ids(rules)
                return {"_config": config, "rules": rules}

            # Format 2: Legacy key-value format (rules as direct properties)
            rules = []
            for key, value in values.items():
                if key == "_config":
                    continue
                if isinstance(value, dict):
                    if "id" not in value:
                        value = {**value, "id": key}
                    rules.append(value)
            return {"_config": config, "rules": rules}

        elif isinstance(values, list):
            # Format 3: Legacy list format
            rules = ensure_rule_ids(values)
            return {"_config": {}, "rules": rules}

        return values


class ExecutionStep(BaseModel):
    """
    Execution step definition (Section 6).

    Defines a single step in the execution flow.
    """

    id: str = Field(
        ...,
        description="Unique step identifier"
    )
    action: str = Field(
        ...,
        min_length=1,
        description="Action to perform"
    )
    output: Optional[str] = Field(
        default=None,
        description="Output variable name"
    )
    based_on: Optional[List[str]] = Field(
        default=None,
        description="Input dependencies from previous steps"
    )
    condition: Optional[str] = Field(
        default=None,
        description="Optional condition for step execution"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate step ID follows snake_case pattern."""
        if not SNAKE_CASE_PATTERN.match(v):
            raise ValueError(
                f"Step ID must be snake_case (e.g., 'validate_input'), got: {v}"
            )
        return v

    class Config:
        extra = "forbid"


class OutputContract(BaseModel):
    """
    Output contract specification (Section 7).

    Defines the expected output format and schema.
    """

    format: OutputFormat = Field(
        ...,
        description="Output format"
    )
    schema_: Dict[str, Any] = Field(
        ...,
        alias="schema",
        description="JSON Schema for output validation"
    )

    class Config:
        extra = "forbid"
        populate_by_name = True


class FailureMode(BaseModel):
    """
    Failure mode definition (Section 8).

    Defines a designed failure scenario with recovery hints.
    """

    code: str = Field(
        ...,
        description="Error code (UPPER_SNAKE_CASE)"
    )
    retryable: bool = Field(
        ...,
        description="Whether this failure can be retried"
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description"
    )
    recovery_hint: Optional[str] = Field(
        default=None,
        description="Suggestion for recovery"
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate error code follows UPPER_SNAKE_CASE pattern."""
        if not UPPER_SNAKE_CASE_PATTERN.match(v):
            raise ValueError(
                f"Error code must be UPPER_SNAKE_CASE (e.g., 'EMPTY_INPUT'), got: {v}"
            )
        return v

    class Config:
        extra = "forbid"


class EdgeCase(BaseModel):
    """
    Edge case definition (Section 9 - Coverage).

    Defines a boundary condition or edge case that must be handled.
    """

    case: str = Field(
        ...,
        min_length=1,
        description="Edge case name/description"
    )
    expected: Dict[str, Any] = Field(
        ...,
        description="Expected behavior for this case"
    )
    input_example: Optional[Any] = Field(
        default=None,
        description="Example input that triggers this case"
    )
    covers_rule: Optional[str] = Field(
        default=None,
        description="Which decision_rule this case tests"
    )
    covers_failure: Optional[str] = Field(
        default=None,
        description="Which failure_mode this case tests"
    )

    class Config:
        extra = "forbid"


class SkillReference(BaseModel):
    """Reference to a related skill."""

    skill: str = Field(..., description="Related skill name")
    reason: str = Field(..., description="Why these skills work together")


class Scenario(BaseModel):
    """Usage scenario definition."""

    name: str = Field(..., description="Scenario name")
    trigger: Optional[str] = Field(
        default=None,
        description="v1.1: What triggers this scenario"
    )
    description: str = Field(..., description="Scenario description")


# v1.1 Models

class Triggers(BaseModel):
    """
    v1.1: When to activate this skill (from Superpowers 'Use when...' pattern).
    """

    use_when: Optional[List[str]] = Field(
        default=None,
        description="Conditions that should trigger this skill"
    )
    do_not_use_when: Optional[List[str]] = Field(
        default=None,
        description="Conditions when this skill should NOT be used"
    )

    class Config:
        extra = "forbid"


class Boundaries(BaseModel):
    """
    v1.1: Clear will/will_not declarations (from SuperClaude).
    """

    will: Optional[List[str]] = Field(
        default=None,
        description="Explicit capabilities this skill provides"
    )
    will_not: Optional[List[str]] = Field(
        default=None,
        description="Explicit limitations and exclusions"
    )

    class Config:
        extra = "forbid"


class BehavioralPhase(BaseModel):
    """
    v1.1: A phase in the behavioral flow.
    """

    phase: str = Field(..., description="Phase name (e.g., analyze, generate, validate)")
    description: str = Field(..., description="What happens in this phase")
    key_actions: Optional[List[str]] = Field(
        default=None,
        description="Key actions performed in this phase"
    )

    class Config:
        extra = "forbid"


class Mistake(BaseModel):
    """v1.1: Common mistake pattern."""

    pattern: str = Field(..., description="Description of the mistake pattern")
    why_bad: str = Field(..., description="Why this pattern is problematic")
    correct: str = Field(..., description="What to do instead")

    class Config:
        extra = "forbid"


class Rationalization(BaseModel):
    """v1.1: Rationalization/excuse pattern."""

    excuse: str = Field(..., description="The rationalization/excuse")
    reality: str = Field(..., description="Why the excuse is wrong")

    class Config:
        extra = "forbid"


class AntiPatterns(BaseModel):
    """
    v1.1: Common mistakes and rationalizations (from Superpowers).
    """

    mistakes: Optional[List[Mistake]] = Field(
        default=None,
        description="Common mistakes AI might make"
    )
    rationalizations: Optional[List[Rationalization]] = Field(
        default=None,
        description="Excuses AI might use to skip rules"
    )
    red_flags: Optional[List[str]] = Field(
        default=None,
        description="Warning signs that the skill is being misused"
    )

    class Config:
        extra = "forbid"


class ContextInfo(BaseModel):
    """
    Context and collaboration info (Section 10 - optional).

    Provides information about how this skill works with others.
    """

    works_with: Optional[List[SkillReference]] = Field(
        default=None,
        description="Related skills that work well together"
    )
    prerequisites: Optional[List[str]] = Field(
        default=None,
        description="What user needs to do before using this skill"
    )
    scenarios: Optional[List[Scenario]] = Field(
        default=None,
        description="Typical usage scenarios"
    )

    class Config:
        extra = "forbid"


class Example(BaseModel):
    """
    Usage example (for Anthropic format).

    Provides concrete input/output examples for documentation.
    """

    name: str = Field(..., description="Example name")
    scenario: Optional[str] = Field(
        default=None,
        description="v1.1: Context/scenario description"
    )
    trigger: Optional[str] = Field(
        default=None,
        description="v1.1: How user triggers this"
    )
    input: Any = Field(..., description="Example input values")
    output: Any = Field(..., description="Expected output")
    explanation: Optional[str] = Field(
        default=None,
        description="Explanation of what happens"
    )

    class Config:
        extra = "forbid"


class SkillSpec(BaseModel):
    """
    Root model for Skill-Spec specification.

    Section Taxonomy v1.0:
    - Core Sections (8 required): skill, inputs, preconditions, non_goals,
      decision_rules, steps, output_contract, failure_modes
    - Coverage Sections (1 required): edge_cases
    - Context Sections (1 optional): context

    v1.2 adds agentskills.io compatibility (https://agentskills.io/specification)
    """

    spec_version: Literal["skill-spec/1.0", "skill-spec/1.1", "skill-spec/1.2"] = Field(
        default="skill-spec/1.0",
        description="Schema version identifier"
    )
    meta: Optional[MetaConfig] = Field(
        default=None,
        alias="_meta",
        description="Meta configuration"
    )

    # Core Sections (8 required)
    skill: SkillMetadata = Field(
        ...,
        description="Skill metadata (Section 1)"
    )
    inputs: List[InputSpec] = Field(
        ...,
        min_length=1,
        description="Input contract (Section 2)"
    )
    preconditions: List[str] = Field(
        ...,
        min_length=1,
        description="Prerequisites (Section 3)"
    )
    non_goals: List[str] = Field(
        ...,
        min_length=1,
        description="What this skill does NOT do (Section 4)"
    )
    decision_rules: Union[Dict[str, Any], List[DecisionRule]] = Field(
        ...,
        description="Decision rules (Section 5)"
    )
    steps: List[ExecutionStep] = Field(
        ...,
        min_length=1,
        description="Execution steps (Section 6)"
    )
    output_contract: OutputContract = Field(
        ...,
        description="Output contract (Section 7)"
    )
    failure_modes: List[FailureMode] = Field(
        ...,
        min_length=1,
        description="Failure modes (Section 8)"
    )

    # Coverage Sections (1 required)
    edge_cases: List[EdgeCase] = Field(
        ...,
        min_length=1,
        description="Edge cases (Section 9 - Coverage)"
    )

    # v1.1 Optional Sections
    triggers: Optional[Triggers] = Field(
        default=None,
        description="v1.1: When to activate this skill"
    )
    boundaries: Optional[Boundaries] = Field(
        default=None,
        description="v1.1: Will/will_not declarations"
    )
    behavioral_flow: Optional[List[BehavioralPhase]] = Field(
        default=None,
        description="v1.1: High-level behavioral phases"
    )
    anti_patterns: Optional[AntiPatterns] = Field(
        default=None,
        description="v1.1: Common mistakes and rationalizations"
    )

    # Context Sections (1 optional)
    context: Optional[ContextInfo] = Field(
        default=None,
        description="Context info (Section 10 - optional)"
    )

    # Optional sections
    examples: Optional[List[Example]] = Field(
        default=None,
        description="Usage examples (recommended for Anthropic format)"
    )

    @model_validator(mode="after")
    def validate_cross_references(self) -> "SkillSpec":
        """Validate cross-references between sections."""
        # Collect all rule IDs using helper to handle various formats
        rule_ids = set()
        if isinstance(self.decision_rules, list):
            rule_ids = {r.id for r in self.decision_rules}
        elif isinstance(self.decision_rules, dict):
            # Handle nested 'rules' key format (_config + rules)
            if "rules" in self.decision_rules and isinstance(self.decision_rules["rules"], list):
                for rule in self.decision_rules["rules"]:
                    if isinstance(rule, dict) and rule.get("id"):
                        rule_ids.add(rule["id"])
            else:
                # Handle rules as direct key-value pairs
                for key, value in self.decision_rules.items():
                    if key != "_config" and isinstance(value, dict):
                        rule_ids.add(value.get("id", key))

        # Collect all failure codes
        failure_codes = {f.code for f in self.failure_modes}

        # Collect all step outputs
        step_outputs = {s.output for s in self.steps if s.output}

        # Validate edge_cases.covers_rule references
        for ec in self.edge_cases:
            if ec.covers_rule and ec.covers_rule not in rule_ids:
                raise ValueError(
                    f"Edge case '{ec.case}' references unknown rule: {ec.covers_rule}"
                )
            if ec.covers_failure and ec.covers_failure not in failure_codes:
                raise ValueError(
                    f"Edge case '{ec.case}' references unknown failure: {ec.covers_failure}"
                )

        # Validate step based_on references
        available_outputs = set()
        for step in self.steps:
            if step.based_on:
                for dep in step.based_on:
                    if dep not in available_outputs:
                        raise ValueError(
                            f"Step '{step.id}' depends on '{dep}' which is not "
                            f"available at this point in the execution flow"
                        )
            if step.output:
                available_outputs.add(step.output)

        return self

    class Config:
        extra = "forbid"
        populate_by_name = True

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "SkillSpec":
        """Parse a SkillSpec from YAML content."""
        import yaml
        data = yaml.safe_load(yaml_content)
        return cls.model_validate(data)

    @classmethod
    def from_file(cls, path: str) -> "SkillSpec":
        """Load a SkillSpec from a YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_yaml(f.read())

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        import yaml
        data = self.model_dump(by_alias=True, exclude_none=True)
        return yaml.dump(data, allow_unicode=True, default_flow_style=False)

    def to_file(self, path: str) -> None:
        """Save to a YAML file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_yaml())
