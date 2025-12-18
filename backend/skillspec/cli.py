"""
Skill-Spec CLI.

Command-line interface for spec-driven skill development.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import yaml

from .validator import ValidationEngine, ValidationResult
from .validator.anthropic_format import AnthropicFormatValidator, AnthropicFormatResult
from .diary import DiaryManager, ensure_gitignore
from .migration import migrate_skill
from .preservation import (
    parse_skill_md,
    merge_with_preservation,
    validate_document_consistency,
    wrap_generated_block,
    GENERATED_START,
    GENERATED_END,
)
from .i18n import (
    I18nContext,
    get_message_catalog,
    t,
    SUPPORTED_LOCALES,
    DEFAULT_LOCALE,
)


# Default paths relative to current directory
DEFAULT_SKILLSPEC_DIR = Path("skillspec")
DEFAULT_SCHEMA_PATH = DEFAULT_SKILLSPEC_DIR / "schema" / "skill_spec_v1.json"
DEFAULT_PATTERNS_DIR = DEFAULT_SKILLSPEC_DIR / "patterns"
DEFAULT_TEMPLATES_DIR = DEFAULT_SKILLSPEC_DIR / "templates"
DEFAULT_DRAFTS_DIR = DEFAULT_SKILLSPEC_DIR / "drafts"
DEFAULT_SKILLS_DIR = DEFAULT_SKILLSPEC_DIR / "skills"
DEFAULT_ARCHIVE_DIR = DEFAULT_SKILLSPEC_DIR / "archive"


def get_skillspec_root() -> Path:
    """Find the skillspec root directory."""
    # Look for skillspec directory in current dir or parents
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "skillspec").is_dir():
            return parent / "skillspec"
        if (parent / "skillspec" / "SKILL_AGENTS.md").exists():
            return parent / "skillspec"
    return DEFAULT_SKILLSPEC_DIR


def ensure_dirs_exist(root: Path) -> None:
    """Ensure all required directories exist."""
    (root / "drafts").mkdir(parents=True, exist_ok=True)
    (root / "skills").mkdir(parents=True, exist_ok=True)
    (root / "archive").mkdir(parents=True, exist_ok=True)


def load_template() -> str:
    """Load the spec.yaml template."""
    root = get_skillspec_root()
    template_path = root / "templates" / "spec.yaml"

    if template_path.exists():
        return template_path.read_text(encoding="utf-8")

    # Default template
    return """# Skill-Spec Template v1.0
spec_version: "skill-spec/1.0"

skill:
  name: "TODO-verb-object"
  version: "1.0.0"
  purpose: "TODO: Single sentence describing what this skill does"
  owner: "TODO-team-name"

inputs:
  - name: TODO_input_name
    type: string
    required: true
    constraints: [not_empty]
    description: "TODO: Precise semantic definition"

preconditions:
  - "TODO: What must be true before this skill runs"

non_goals:
  - "TODO: Explicitly state what is out of scope"

decision_rules:
  _config:
    match_strategy: first_match
    conflict_resolution: error
  rules:
    - id: rule_default
      is_default: true
      when: true
      then:
        status: success
        path: default

steps:
  - id: process
    action: TODO_main_action
    output: result

output_contract:
  format: json
  schema:
    type: object
    required: [status]
    properties:
      status:
        enum: [success, error]

failure_modes:
  - code: VALIDATION_ERROR
    retryable: false
    description: "Input validation failed"

edge_cases:
  - case: empty_input
    expected:
      status: error
      code: VALIDATION_ERROR
"""


def find_skill(name: str) -> Optional[Path]:
    """Find a skill by name in drafts or skills directories."""
    root = get_skillspec_root()

    # Check drafts first
    draft_path = root / "drafts" / name / "spec.yaml"
    if draft_path.exists():
        return draft_path

    # Check skills
    skill_path = root / "skills" / name / "spec.yaml"
    if skill_path.exists():
        return skill_path

    return None


def get_skill_status(name: str) -> str:
    """Get the status of a skill."""
    root = get_skillspec_root()

    if (root / "drafts" / name).exists():
        return "draft"
    elif (root / "skills" / name).exists():
        return "published"
    else:
        return "unknown"


# Global i18n context
_i18n_context: Optional[I18nContext] = None


def get_i18n_context() -> I18nContext:
    """Get the current i18n context."""
    global _i18n_context
    if _i18n_context is None:
        # Try to load from project.yaml
        root = get_skillspec_root()
        project_yaml = root.parent / "project.yaml"
        if not project_yaml.exists():
            project_yaml = root / "project.yaml"
        _i18n_context = I18nContext.from_project_yaml(project_yaml)
    return _i18n_context


def set_i18n_context(ctx: I18nContext) -> None:
    """Set the global i18n context."""
    global _i18n_context
    _i18n_context = ctx


@click.group()
@click.version_option(version="1.0.0")
@click.option("--locale", type=click.Choice(["en", "zh"]), default=None,
              help="Report/output language (en/zh). Overrides project.yaml setting.")
@click.option("--patterns", type=click.Choice(["en", "zh", "union"]), default=None,
              help="Forbidden patterns language (en/zh/union). 'union' checks both.")
@click.option("--template-locale", type=click.Choice(["en", "zh"]), default=None,
              help="SKILL.md template language (en/zh).")
@click.pass_context
def cli(ctx: click.Context, locale: Optional[str], patterns: Optional[str],
        template_locale: Optional[str]):
    """Skill-Spec: Spec-driven skill development.

    Multi-language support: Use --locale for report language, --patterns for
    forbidden pattern detection language, --template-locale for SKILL.md generation.

    Default settings are loaded from project.yaml. CLI options override these.
    """
    # Initialize context
    ctx.ensure_object(dict)

    # Create base i18n context with defaults
    i18n_ctx = I18nContext()

    # Try to load from project.yaml (deferred to avoid issues)
    try:
        root = get_skillspec_root()
        project_yaml = root.parent / "project.yaml"
        if not project_yaml.exists():
            project_yaml = root / "project.yaml"
        i18n_ctx = I18nContext.from_project_yaml(project_yaml)

        # Initialize message catalog with correct locale
        messages_dir = root / "templates" / "messages"
        get_message_catalog(messages_dir)
    except Exception:
        pass  # Continue with defaults if skillspec root not found

    # Override with CLI options
    if locale:
        i18n_ctx.report_locale = locale
        i18n_ctx.content_locale = locale
    if patterns:
        i18n_ctx.patterns_locale = patterns
    if template_locale:
        i18n_ctx.template_locale = template_locale

    # Store in click context and global
    ctx.obj["i18n"] = i18n_ctx
    set_i18n_context(i18n_ctx)


def get_package_data_dir() -> Path:
    """Get the package data directory containing templates, schema, etc."""
    # First try relative to this file (development mode)
    pkg_dir = Path(__file__).parent.parent.parent / "skillspec"
    if pkg_dir.exists() and (pkg_dir / "SKILL_AGENTS.md").exists():
        return pkg_dir

    # Try installed package data
    import importlib.resources
    try:
        # Python 3.9+
        return Path(importlib.resources.files("skillspec"))  # type: ignore
    except (AttributeError, TypeError):
        # Fallback for older Python
        import pkg_resources
        return Path(pkg_resources.resource_filename("skillspec", ""))


def detect_ai_tools(project_dir: Path) -> list[str]:
    """Detect which AI tools are configured in the project."""
    tools = []

    # Claude Code - look for .claude/ directory
    if (project_dir / ".claude").is_dir():
        tools.append("claude-code")

    # Cursor - look for .cursor/ directory
    if (project_dir / ".cursor").is_dir():
        tools.append("cursor")

    # Cline - look for .cline/ directory
    if (project_dir / ".cline").is_dir():
        tools.append("cline")

    # Codex (OpenAI) - look for .codex/ directory
    if (project_dir / ".codex").is_dir():
        tools.append("codex")

    # VSCode - look for .vscode/ directory (CodeBuddy, etc.)
    if (project_dir / ".vscode").is_dir():
        tools.append("vscode")

    return tools


def copy_tree(src: Path, dst: Path, overwrite: bool = False) -> int:
    """Copy directory tree, return count of copied files."""
    count = 0
    if not src.exists():
        return count

    dst.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        dst_item = dst / item.name
        if item.is_dir():
            count += copy_tree(item, dst_item, overwrite)
        else:
            if not dst_item.exists() or overwrite:
                shutil.copy2(item, dst_item)
                count += 1
    return count


@cli.command()
@click.option("--force", is_flag=True, help="Overwrite existing files")
@click.option("--no-commands", is_flag=True, help="Skip slash command installation")
@click.option("--tool", type=click.Choice(["claude-code", "cursor", "cline", "codex", "auto"]),
              default="auto", help="Target AI tool for slash commands")
@click.option("--custom-dir", type=click.Path(), default=None,
              help="Custom directory for slash commands (for unsupported AI tools)")
def setup(force: bool, no_commands: bool, tool: str, custom_dir: str):
    """Initialize Skill-Spec in current project.

    This command sets up the skillspec/ directory structure and installs
    slash commands for AI-assisted skill development.

    \b
    What it does:
    1. Creates skillspec/ directory with templates, schema, patterns
    2. Copies SKILL_AGENTS.md (AI guidance file)
    3. Installs slash commands for your AI tool (Claude Code, Cursor, Cline, Codex)
    4. Creates project.yaml for i18n configuration

    \b
    Examples:
        # Auto-detect AI tools
        skillspec setup

        # Specify a known tool
        skillspec setup --tool cursor

        # Use custom directory for unsupported AI tools
        skillspec setup --custom-dir .my-agent/commands/skill-spec

    After setup, use /skill-spec:proposal <name> in your AI tool to create skills.
    """
    project_dir = Path.cwd()
    pkg_data = get_package_data_dir()

    click.echo("Initializing Skill-Spec in current project...")
    click.echo(f"  Project: {project_dir}")
    click.echo(f"  Package data: {pkg_data}")
    click.echo()

    # 1. Create skillspec/ directory structure
    skillspec_dir = project_dir / "skillspec"
    if skillspec_dir.exists() and not force:
        click.echo(f"  skillspec/ already exists. Use --force to overwrite.")
    else:
        skillspec_dir.mkdir(parents=True, exist_ok=True)

        # Copy subdirectories
        subdirs = ["schema", "templates", "patterns"]
        for subdir in subdirs:
            src = pkg_data / subdir
            dst = skillspec_dir / subdir
            if src.exists():
                count = copy_tree(src, dst, force)
                click.echo(f"  Created skillspec/{subdir}/ ({count} files)")

        # Create empty directories
        for dirname in ["drafts", "skills", "archive"]:
            (skillspec_dir / dirname).mkdir(exist_ok=True)
            click.echo(f"  Created skillspec/{dirname}/")

    # 2. Copy SKILL_AGENTS.md
    agents_src = pkg_data / "SKILL_AGENTS.md"
    agents_dst = skillspec_dir / "SKILL_AGENTS.md"
    if agents_src.exists():
        if not agents_dst.exists() or force:
            shutil.copy2(agents_src, agents_dst)
            click.echo("  Created skillspec/SKILL_AGENTS.md")
        else:
            click.echo("  skillspec/SKILL_AGENTS.md already exists (skipped)")
    else:
        click.echo("  Warning: SKILL_AGENTS.md not found in package", err=True)

    # 3. Install slash commands
    if not no_commands:
        # Find source commands
        commands_src = pkg_data.parent / ".claude" / "commands" / "skill-spec"
        if not commands_src.exists():
            # Try alternative location
            commands_src = Path(__file__).parent.parent.parent.parent / ".claude" / "commands" / "skill-spec"

        if not commands_src.exists():
            click.echo("  Warning: Slash commands not found in package", err=True)
            click.echo(f"    Searched: {commands_src}", err=True)
        elif custom_dir:
            # Custom directory for unsupported AI tools
            commands_dst = project_dir / custom_dir
            commands_dst.mkdir(parents=True, exist_ok=True)
            count = copy_tree(commands_src, commands_dst, force)
            click.echo(f"  Installed slash commands to custom directory ({count} files)")
            click.echo(f"    Path: {commands_dst}")
        else:
            # Detect AI tools
            if tool == "auto":
                detected_tools = detect_ai_tools(project_dir)
                if not detected_tools:
                    # Default to Claude Code
                    detected_tools = ["claude-code"]
                    click.echo("  No AI tools detected, defaulting to Claude Code")
                else:
                    click.echo(f"  Detected AI tools: {', '.join(detected_tools)}")
            else:
                detected_tools = [tool]

            # Map AI tools to their command directories
            tool_dirs = {
                "claude-code": ".claude",
                "cursor": ".cursor",
                "cline": ".cline",
                "codex": ".codex",
            }

            for ai_tool in detected_tools:
                if ai_tool not in tool_dirs:
                    continue

                commands_dst = project_dir / tool_dirs[ai_tool] / "commands" / "skill-spec"
                commands_dst.mkdir(parents=True, exist_ok=True)
                count = copy_tree(commands_src, commands_dst, force)
                click.echo(f"  Installed slash commands for {ai_tool} ({count} files)")

    # 4. Create project.yaml if not exists
    project_yaml = project_dir / "project.yaml"
    if not project_yaml.exists():
        project_yaml_content = """# Skill-Spec Project Configuration
# Generated by: skillspec setup

skill_spec:
  # Report language: en | zh
  report_locale: en

  # Forbidden patterns language: en | zh | union (check both)
  patterns_locale: union

  # SKILL.md template language: en | zh
  template_locale: en

  # Default compliance policy (optional)
  # default_policy: skillspec/policies/enterprise.yaml
"""
        project_yaml.write_text(project_yaml_content, encoding="utf-8")
        click.echo("  Created project.yaml")
    else:
        click.echo("  project.yaml already exists (skipped)")

    click.echo()
    click.echo("Setup complete!")
    click.echo()
    click.echo("Next steps:")
    click.echo("  1. Use /skill-spec:proposal <name> to create a new skill interactively")
    click.echo("  2. Or run: skillspec init <name> for manual creation")
    click.echo()
    click.echo("Directory structure created:")
    click.echo("  skillspec/")
    click.echo("    SKILL_AGENTS.md    <- AI guidance (must read)")
    click.echo("    schema/            <- JSON Schema")
    click.echo("    templates/         <- Spec templates")
    click.echo("    patterns/          <- Forbidden patterns")
    click.echo("    drafts/            <- Work in progress")
    click.echo("    skills/            <- Published skills")
    click.echo("    archive/           <- Archived versions")


@cli.command("list")
def list_skills():
    """List all skills (drafts + published)."""
    root = get_skillspec_root()
    ensure_dirs_exist(root)

    drafts_dir = root / "drafts"
    skills_dir = root / "skills"

    click.echo("Skills:")
    click.echo()

    # List drafts
    if drafts_dir.exists():
        drafts = [d.name for d in drafts_dir.iterdir() if d.is_dir()]
        if drafts:
            click.echo("  Drafts:")
            for name in sorted(drafts):
                spec_path = drafts_dir / name / "spec.yaml"
                status = "valid" if spec_path.exists() else "no spec"
                click.echo(f"    - {name} ({status})")
        else:
            click.echo("  Drafts: (none)")

    # List published skills
    if skills_dir.exists():
        skills = [d.name for d in skills_dir.iterdir() if d.is_dir()]
        if skills:
            click.echo("  Published:")
            for name in sorted(skills):
                spec_path = skills_dir / name / "spec.yaml"
                has_skill_md = (skills_dir / name / "SKILL.md").exists()
                status = "complete" if has_skill_md else "spec only"
                click.echo(f"    - {name} ({status})")
        else:
            click.echo("  Published: (none)")


@cli.command()
@click.argument("name")
def init(name: str):
    """Scaffold a new skill in drafts/."""
    root = get_skillspec_root()
    ensure_dirs_exist(root)

    # Validate name format
    import re
    if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", name):
        click.echo(f"Error: Invalid skill name '{name}'", err=True)
        click.echo("Name must be kebab-case (e.g., 'extract-api-contract')", err=True)
        sys.exit(1)

    # Check if already exists
    draft_dir = root / "drafts" / name
    if draft_dir.exists():
        click.echo(f"Error: Skill '{name}' already exists in drafts/", err=True)
        sys.exit(1)

    skill_dir = root / "skills" / name
    if skill_dir.exists():
        click.echo(f"Error: Skill '{name}' already exists in skills/", err=True)
        sys.exit(1)

    # Create directory and spec.yaml
    draft_dir.mkdir(parents=True)
    spec_path = draft_dir / "spec.yaml"

    # Load and customize template
    template = load_template()
    template = template.replace("TODO-verb-object", name)

    spec_path.write_text(template, encoding="utf-8")

    click.echo(f"Created skill draft: {draft_dir}")
    click.echo(f"  spec.yaml: {spec_path}")
    click.echo()
    click.echo("Next steps:")
    click.echo("  1. Edit spec.yaml to fill in all TODO sections")
    click.echo(f"  2. Run: skillspec validate {name} --strict")
    click.echo(f"  3. Run: skillspec generate {name}")


@cli.command()
@click.argument("name")
def show(name: str):
    """Display a skill spec."""
    spec_path = find_skill(name)

    if not spec_path:
        click.echo(f"Error: Skill '{name}' not found", err=True)
        sys.exit(1)

    status = get_skill_status(name)
    click.echo(f"Skill: {name} ({status})")
    click.echo(f"Path: {spec_path}")
    click.echo("-" * 40)
    click.echo(spec_path.read_text(encoding="utf-8"))


@cli.command()
@click.argument("name")
@click.option("--strict", is_flag=True, help="Fail on warnings and include format check")
@click.option("--policy", "policy_paths", multiple=True, type=click.Path(exists=True),
              help="Path to policy YAML file (can be specified multiple times)")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]),
              default="text", help="Output format")
@click.pass_context
def validate(ctx: click.Context, name: str, strict: bool, policy_paths: tuple,
             output_format: str):
    """Validate a skill spec.

    With --strict mode, validation also includes format check and will load
    default_policy from project.yaml if configured.

    Use --policy to specify enterprise policy files for compliance validation.
    """
    spec_path = find_skill(name)

    if not spec_path:
        i18n = get_i18n_context()
        msg = t("cli.skill_not_found", locale=i18n.report_locale, name=name)
        click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    root = get_skillspec_root()

    # Get patterns language from i18n context
    i18n = get_i18n_context()
    patterns_locale = i18n.patterns_locale

    # Map locale to languages for validator
    if patterns_locale == "union":
        languages = ["en", "zh"]
    else:
        languages = [patterns_locale]

    # Collect policy files
    policy_files = []

    # If strict mode, check for default_policy in project.yaml
    if strict:
        project_yaml = root.parent / "project.yaml"
        if not project_yaml.exists():
            project_yaml = root / "project.yaml"
        if project_yaml.exists():
            try:
                with open(project_yaml, "r", encoding="utf-8") as f:
                    project_data = yaml.safe_load(f) or {}
                default_policy = project_data.get("default_policy")
                if default_policy:
                    # Resolve relative path
                    default_policy_path = root.parent / default_policy
                    if not default_policy_path.exists():
                        default_policy_path = root / default_policy
                    if default_policy_path.exists():
                        policy_files.append(default_policy_path)
            except yaml.YAMLError:
                pass

    # Add command-line specified policies
    for policy_path in policy_paths:
        policy_files.append(Path(policy_path))

    engine = ValidationEngine(
        schema_path=root / "schema" / "skill_spec_v1.json",
        patterns_dir=root / "patterns",
        languages=languages,
        policy_files=policy_files if policy_files else None,
    )

    result = engine.validate_file(spec_path, strict=strict)

    # In strict mode, also validate SKILL.md format if it exists
    format_result = None
    if strict:
        skill_md_path = spec_path.parent / "SKILL.md"
        if skill_md_path.exists():
            format_validator = AnthropicFormatValidator()
            format_result = format_validator.validate_file(skill_md_path)

    # Determine overall result (in strict mode, format check is also required)
    overall_valid = result.valid
    format_failed_in_strict = False
    if strict and format_result and not format_result.valid:
        overall_valid = False
        format_failed_in_strict = True

    if output_format == "json":
        output_data = result.to_dict()
        if format_result:
            output_data["anthropic_format"] = format_result.to_dict()
        output_data["overall_valid"] = overall_valid
        click.echo(json.dumps(output_data, indent=2))
    else:
        _print_validation_result(result, name)
        if format_result:
            click.echo()
            _print_format_result(format_result)

        # Show clear overall status in strict mode
        if strict:
            click.echo()
            click.echo("-" * 40)
            if overall_valid:
                click.secho("Overall (--strict): PASSED", fg="green", bold=True)
            else:
                click.secho("Overall (--strict): FAILED", fg="red", bold=True)
                if format_failed_in_strict:
                    click.echo("  Reason: Anthropic format check failed")
                if not result.valid:
                    click.echo("  Reason: Spec validation failed")

    sys.exit(0 if overall_valid else 1)


def _print_validation_result(result: ValidationResult, name: str) -> None:
    """Print validation result in text format."""
    status = "PASSED" if result.valid else "FAILED"
    color = "green" if result.valid else "red"

    click.echo()
    click.secho(f"Validation {status}: {name}", fg=color, bold=True)
    click.echo()

    # Schema errors
    if result.schema_result and result.schema_result.errors:
        click.secho("Schema Errors:", fg="red")
        for error in result.schema_result.errors:
            click.echo(f"  - {error}")
        click.echo()

    # Quality violations
    if result.quality_result and result.quality_result.violations:
        errors = [v for v in result.quality_result.violations if v.severity == "error"]
        warnings = [v for v in result.quality_result.violations if v.severity == "warning"]

        if errors:
            click.secho("Quality Errors:", fg="red")
            for v in errors:
                click.echo(f"  [{v.path}] {v.category}: '{v.matched_text}'")
                click.echo(f"    Fix: {v.fix_suggestion}")
            click.echo()

        if warnings:
            click.secho("Quality Warnings:", fg="yellow")
            for v in warnings:
                click.echo(f"  [{v.path}] {v.category}: '{v.matched_text}'")
            click.echo()

    # Coverage gaps
    if result.coverage_result and result.coverage_result.gaps:
        click.secho("Coverage Gaps:", fg="yellow")
        for gap in result.coverage_result.gaps:
            severity_color = "red" if gap.severity == "error" else "yellow"
            click.secho(f"  [{gap.gap_type}] {gap.item}: {gap.description}",
                       fg=severity_color)
        click.echo()

    # Consistency issues
    if result.consistency_result and result.consistency_result.issues:
        click.secho("Consistency Issues:", fg="yellow")
        for issue in result.consistency_result.issues:
            click.echo(f"  {issue.source} -> {issue.target}: {issue.description}")
        click.echo()

    # Summary
    click.echo("-" * 40)
    click.echo(f"Errors: {result.total_errors}")
    click.echo(f"Warnings: {result.total_warnings}")

    if result.coverage_result:
        metrics = result.coverage_result.metrics
        click.echo(f"Structural Coverage: {metrics.structural_score}%")
        click.echo(f"Behavioral Coverage: {metrics.behavioral_score}%")


def _print_format_result(result: AnthropicFormatResult) -> None:
    """Print Anthropic format validation result."""
    status = "PASSED" if result.valid else "FAILED"
    color = "green" if result.valid else "red"

    click.secho(f"Anthropic Format Check: {status}", fg=color, bold=True)
    click.echo(f"  Compliance Score: {result.compliance_score:.0%}")
    click.echo()

    # Frontmatter errors
    if result.frontmatter.errors:
        click.secho("Frontmatter Errors:", fg="red")
        for err in result.frontmatter.errors:
            click.echo(f"  - {err}")
        click.echo()

    # Missing required sections
    missing_required = [s for s in result.sections
                        if s.requirement.value == "required" and not s.present]
    if missing_required:
        click.secho("Missing Required Sections:", fg="red")
        for s in missing_required:
            click.echo(f"  - {s.name}")
        click.echo()

    # Missing recommended sections
    missing_recommended = [s for s in result.sections
                          if s.requirement.value == "recommended" and not s.present]
    if missing_recommended:
        click.secho("Missing Recommended Sections:", fg="yellow")
        for s in missing_recommended:
            click.echo(f"  - {s.name}")
        click.echo()

    # Example validation errors
    example_errors = [e for e in result.examples if e.errors]
    if example_errors:
        click.secho("Example Format Issues:", fg="yellow")
        for ex in example_errors:
            for err in ex.errors:
                click.echo(f"  - {err}")


@cli.command("check-format")
@click.argument("name")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]),
              default="text", help="Output format")
def check_format(name: str, output_format: str):
    """Check SKILL.md format against Anthropic requirements."""
    spec_path = find_skill(name)

    if not spec_path:
        click.echo(f"Error: Skill '{name}' not found", err=True)
        sys.exit(1)

    skill_md_path = spec_path.parent / "SKILL.md"

    if not skill_md_path.exists():
        click.echo(f"Error: SKILL.md not found. Run 'skillspec generate {name}' first.",
                   err=True)
        sys.exit(1)

    validator = AnthropicFormatValidator()
    result = validator.validate_file(skill_md_path)

    if output_format == "json":
        click.echo(json.dumps(result.to_dict(), indent=2))
    else:
        _print_format_result(result)

    sys.exit(0 if result.valid else 1)


@cli.command("check-consistency")
@click.argument("name")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]),
              default="text", help="Output format")
def check_consistency(name: str, output_format: str):
    """Check if generated blocks can be reproduced from spec.

    Validates that the generated blocks in SKILL.md match what would be
    generated from the current spec.yaml. This ensures the spec and
    SKILL.md stay in sync.
    """
    spec_path = find_skill(name)

    if not spec_path:
        click.echo(f"Error: Skill '{name}' not found", err=True)
        sys.exit(1)

    skill_md_path = spec_path.parent / "SKILL.md"

    if not skill_md_path.exists():
        click.echo(f"Error: SKILL.md not found. Run 'skillspec generate {name}' first.",
                   err=True)
        sys.exit(1)

    # Load spec and generate expected content
    with open(spec_path, "r", encoding="utf-8") as f:
        spec_data = yaml.safe_load(f)

    expected_content = _generate_skill_md(spec_data)
    actual_content = skill_md_path.read_text(encoding="utf-8")

    # Validate consistency
    result = validate_document_consistency(actual_content, expected_content)

    if output_format == "json":
        click.echo(json.dumps(result.to_dict(), indent=2))
    else:
        status = "PASSED" if result.valid else "FAILED"
        color = "green" if result.valid else "red"

        click.echo()
        click.secho(f"Consistency Check: {status}", fg=color, bold=True)
        click.echo(f"  Generated blocks checked: {result.blocks_checked}")

        if result.inconsistencies:
            click.echo()
            click.secho("Inconsistencies found:", fg="yellow")
            for issue in result.inconsistencies:
                click.echo(f"  - {issue}")
            click.echo()
            click.echo("Run 'skillspec generate <name>' to update generated blocks.")
        else:
            click.echo("  All generated blocks are up-to-date with spec.yaml")

    sys.exit(0 if result.valid else 1)


@cli.command()
@click.argument("name")
@click.option("--force", is_flag=True, help="Overwrite existing SKILL.md including manual blocks")
@click.option("--no-preserve", is_flag=True, help="Regenerate without preservation markers")
def generate(name: str, force: bool, no_preserve: bool):
    """Generate SKILL.md from spec.yaml.

    By default, uses preservation protocol to keep manual blocks intact.
    Manual blocks are wrapped in <!-- skillspec:manual:start/end --> markers.
    Generated content is wrapped in <!-- skillspec:generated:start/end --> markers.

    Use --force to override all content including manual blocks.
    Use --no-preserve to generate without any markers (legacy behavior).
    """
    spec_path = find_skill(name)

    if not spec_path:
        click.echo(f"Error: Skill '{name}' not found", err=True)
        sys.exit(1)

    # Load spec
    with open(spec_path, "r", encoding="utf-8") as f:
        spec_data = yaml.safe_load(f)

    # Determine output path
    skill_dir = spec_path.parent
    skill_md_path = skill_dir / "SKILL.md"

    # Generate new content from spec
    new_content = _generate_skill_md(spec_data)

    # Handle existing file with preservation
    if skill_md_path.exists():
        existing_content = skill_md_path.read_text(encoding="utf-8")

        if no_preserve:
            # Legacy behavior: just check if we can overwrite
            if not force:
                click.echo(f"SKILL.md already exists. Use --force to overwrite.", err=True)
                sys.exit(1)
            final_content = new_content
        else:
            # Preservation protocol
            preservation_result = merge_with_preservation(
                existing_content=existing_content,
                new_generated_content=new_content,
                force=force
            )

            if not preservation_result.success:
                click.echo("Error during preservation merge:", err=True)
                for error in preservation_result.errors:
                    click.echo(f"  - {error}", err=True)
                sys.exit(1)

            final_content = preservation_result.merged_content

            # Report preservation stats
            if preservation_result.manual_blocks_preserved > 0:
                click.echo(f"Preserved {preservation_result.manual_blocks_preserved} manual block(s)")

            for warning in preservation_result.warnings:
                click.secho(f"Warning: {warning}", fg="yellow")
    else:
        # No existing file - wrap new content in generated markers
        if no_preserve:
            final_content = new_content
        else:
            final_content = wrap_generated_block(new_content)

    skill_md_path.write_text(final_content, encoding="utf-8")
    click.echo(f"Generated: {skill_md_path}")


def _generate_skill_md(spec_data: dict) -> str:
    """Generate SKILL.md content from spec data."""
    skill = spec_data.get("skill", {})
    inputs = spec_data.get("inputs", [])
    non_goals = spec_data.get("non_goals", [])
    preconditions = spec_data.get("preconditions", [])
    decision_rules = spec_data.get("decision_rules", {})
    steps = spec_data.get("steps", [])
    edge_cases = spec_data.get("edge_cases", [])
    output_contract = spec_data.get("output_contract", {})
    failure_modes = spec_data.get("failure_modes", [])
    context = spec_data.get("context", {})

    # Extract triggers from decision rules for description
    triggers = []
    # Handle all decision_rules formats:
    # 1. Canonical: {"_config": {...}, "rules": [...]}
    # 2. Legacy key-value: {"_config": {...}, "rule_id": {...}, ...}
    # 3. Legacy list: [{...}, {...}]
    if isinstance(decision_rules, list):
        rules = decision_rules
    elif isinstance(decision_rules, dict) and "rules" in decision_rules:
        rules = decision_rules["rules"]
    elif isinstance(decision_rules, dict):
        rules = [v for k, v in decision_rules.items() if k != "_config"]
    else:
        rules = []
    for rule in rules[:3]:  # First 3 rules
        if isinstance(rule, dict) and rule.get("when") and rule.get("when") is not True:
            triggers.append(str(rule["when"]))

    trigger_text = " | ".join(triggers) if triggers else "general use"

    lines = []

    # Frontmatter
    lines.append("---")
    lines.append(f'name: "{skill.get("name", "")}"')
    lines.append(f'description: "{skill.get("purpose", "")} Use when: {trigger_text}"')
    lines.append("---")
    lines.append("")

    # Title
    title = skill.get("name", "").replace("-", " ").title()
    lines.append(f"# {title}")
    lines.append("")

    # Purpose
    lines.append("## Purpose")
    lines.append("")
    lines.append(skill.get("purpose", ""))
    lines.append("")

    # Inputs
    lines.append("## Inputs")
    lines.append("")
    for inp in inputs:
        req = "required" if inp.get("required") else "optional"
        lines.append(f"- **{inp.get('name')}** ({inp.get('type')}, {req})")
        if inp.get("description"):
            lines.append(f"  {inp['description']}")
        if inp.get("constraints"):
            constraints = ", ".join(str(c) for c in inp["constraints"])
            lines.append(f"  Constraints: {constraints}")
    lines.append("")

    # What This Skill Does NOT Do
    if non_goals:
        lines.append("## What This Skill Does NOT Do")
        lines.append("")
        for goal in non_goals:
            lines.append(f"- {goal}")
        lines.append("")

    # Prerequisites
    if preconditions:
        lines.append("## Prerequisites")
        lines.append("")
        for prereq in preconditions:
            lines.append(f"- {prereq}")
        lines.append("")

    # Decision Criteria
    if rules:
        lines.append("## Decision Criteria")
        lines.append("")
        for rule in rules:
            if isinstance(rule, dict):
                rule_id = rule.get("id", "rule")
                when = rule.get("when", "")
                then = rule.get("then", {})
                lines.append(f"### {rule_id}")
                lines.append(f"- **When**: `{when}`")
                lines.append(f"- **Then**: `{then}`")
                lines.append("")

    # Workflow
    if steps:
        lines.append("## Workflow")
        lines.append("")
        for i, step in enumerate(steps, 1):
            action = step.get("action", "")
            output = step.get("output", "")
            output_text = f" -> `{output}`" if output else ""
            lines.append(f"{i}. **{action}**{output_text}")
        lines.append("")

    # Edge Cases
    if edge_cases:
        lines.append("## Edge Cases")
        lines.append("")
        for ec in edge_cases:
            lines.append(f"- **{ec.get('case')}**: `{ec.get('expected')}`")
        lines.append("")

    # Output Format
    lines.append("## Output Format")
    lines.append("")
    lines.append(f"Format: `{output_contract.get('format', 'json')}`")
    lines.append("")
    lines.append("```json")
    schema = output_contract.get("schema", {})
    lines.append(json.dumps(schema, indent=2))
    lines.append("```")
    lines.append("")

    # Error Handling
    if failure_modes:
        lines.append("## Error Handling")
        lines.append("")
        for fm in failure_modes:
            retryable = "Retryable" if fm.get("retryable") else "Non-retryable"
            lines.append(f"- **{fm.get('code')}**: {retryable}")
            if fm.get("description"):
                lines.append(f"  {fm['description']}")
        lines.append("")

    # Works Well With
    if context.get("works_with"):
        lines.append("## Works Well With")
        lines.append("")
        for ref in context["works_with"]:
            lines.append(f"- **{ref.get('skill')}**: {ref.get('reason')}")
        lines.append("")

    return "\n".join(lines)


@cli.command()
@click.argument("name")
def test(name: str):
    """Test implementation against spec."""
    spec_path = find_skill(name)

    if not spec_path:
        click.echo(f"Error: Skill '{name}' not found", err=True)
        sys.exit(1)

    skill_dir = spec_path.parent
    skill_md_path = skill_dir / "SKILL.md"

    if not skill_md_path.exists():
        click.echo(f"Error: SKILL.md not found. Run 'skillspec generate {name}' first.",
                  err=True)
        sys.exit(1)

    # Basic structure test
    click.echo(f"Testing skill: {name}")
    click.echo()

    # Load spec
    with open(spec_path, "r", encoding="utf-8") as f:
        spec_data = yaml.safe_load(f)

    # Load SKILL.md
    skill_md_content = skill_md_path.read_text(encoding="utf-8")

    errors = []
    warnings = []

    # Check frontmatter exists
    if not skill_md_content.startswith("---"):
        errors.append("SKILL.md missing frontmatter")

    # Check required sections exist
    required_sections = ["Purpose", "Inputs", "Output Format"]
    for section in required_sections:
        if f"## {section}" not in skill_md_content:
            errors.append(f"Missing required section: {section}")

    # Check skill name in frontmatter
    skill_name = spec_data.get("skill", {}).get("name", "")
    if skill_name and f'name: "{skill_name}"' not in skill_md_content:
        warnings.append(f"Skill name mismatch in frontmatter")

    # Print results
    if errors:
        click.secho("Errors:", fg="red")
        for e in errors:
            click.echo(f"  - {e}")
        click.echo()

    if warnings:
        click.secho("Warnings:", fg="yellow")
        for w in warnings:
            click.echo(f"  - {w}")
        click.echo()

    if not errors:
        click.secho("Test PASSED", fg="green")
        sys.exit(0)
    else:
        click.secho("Test FAILED", fg="red")
        sys.exit(1)


@cli.command()
@click.argument("name")
def publish(name: str):
    """Move skill from drafts/ to skills/."""
    root = get_skillspec_root()
    draft_dir = root / "drafts" / name
    skills_dir = root / "skills" / name

    if not draft_dir.exists():
        click.echo(f"Error: Skill '{name}' not found in drafts/", err=True)
        sys.exit(1)

    if skills_dir.exists():
        click.echo(f"Error: Skill '{name}' already exists in skills/", err=True)
        click.echo("Use 'skillspec archive' first to archive the old version.", err=True)
        sys.exit(1)

    # Validate before publishing
    spec_path = draft_dir / "spec.yaml"
    engine = ValidationEngine(
        schema_path=root / "schema" / "skill_spec_v1.json",
        patterns_dir=root / "patterns",
    )
    result = engine.validate_file(spec_path, strict=True)

    if not result.valid:
        click.echo("Error: Skill validation failed. Fix errors before publishing.", err=True)
        _print_validation_result(result, name)
        sys.exit(1)

    # Move to skills
    shutil.move(str(draft_dir), str(skills_dir))
    click.echo(f"Published: {name}")
    click.echo(f"  From: {draft_dir}")
    click.echo(f"  To: {skills_dir}")


@cli.command()
@click.argument("name")
def archive(name: str):
    """Archive a published skill."""
    root = get_skillspec_root()
    skills_dir = root / "skills" / name
    archive_dir = root / "archive"

    if not skills_dir.exists():
        click.echo(f"Error: Skill '{name}' not found in skills/", err=True)
        sys.exit(1)

    # Create archive name with date
    date_str = datetime.now().strftime("%Y-%m-%d")
    archive_name = f"{date_str}-{name}"
    archive_path = archive_dir / archive_name

    # Ensure archive directory exists
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Move to archive
    shutil.move(str(skills_dir), str(archive_path))
    click.echo(f"Archived: {name}")
    click.echo(f"  To: {archive_path}")


@cli.command()
@click.argument("name")
@click.option("--summary", is_flag=True, help="Show summary only")
@click.option("--quality", is_flag=True, help="Show quality report")
@click.option("--coverage", is_flag=True, help="Show coverage report")
@click.option("--tags", is_flag=True, help="Show tag taxonomy report")
@click.option("--compliance", is_flag=True, help="Show compliance report")
@click.option("--consistency", is_flag=True, help="Show consistency report")
@click.option("--with-evidence", is_flag=True, help="Include diary evidence")
@click.option("--policy", "policy_paths", multiple=True, type=click.Path(exists=True),
              help="Path to policy YAML file for compliance check")
@click.option("--format", "output_format", type=click.Choice(["text", "json", "markdown"]),
              default="text", help="Output format (text for terminal, json for machine, markdown for documentation)")
@click.option("--output-dir", type=click.Path(),
              help="Output directory for dual output (Markdown + JSON)")
def report(name: str, summary: bool, quality: bool, coverage: bool,
           tags: bool, compliance: bool, consistency: bool,
           with_evidence: bool, policy_paths: tuple, output_format: str,
           output_dir: Optional[str]):
    """Generate a quality report for a skill.

    When --compliance is specified, you can provide --policy files to check.
    Otherwise, uses default_policy from project.yaml if configured.

    Use --output-dir to generate both Markdown and JSON reports in a directory.
    """
    import time
    from .report import generate_compliance_report, ReportTimer

    spec_path = find_skill(name)

    if not spec_path:
        click.echo(f"Error: Skill '{name}' not found", err=True)
        sys.exit(1)

    root = get_skillspec_root()

    # Collect policy files if compliance is requested
    policy_files = None
    if compliance:
        policy_files = []
        # Add command-line specified policies
        for policy_path in policy_paths:
            policy_files.append(Path(policy_path))

        # If no policies specified, try to load default from project.yaml
        if not policy_files:
            project_yaml = root.parent / "project.yaml"
            if not project_yaml.exists():
                project_yaml = root / "project.yaml"
            if project_yaml.exists():
                try:
                    with open(project_yaml, "r", encoding="utf-8") as f:
                        project_data = yaml.safe_load(f) or {}
                    default_policy = project_data.get("default_policy")
                    if default_policy:
                        default_policy_path = root.parent / default_policy
                        if not default_policy_path.exists():
                            default_policy_path = root / default_policy
                        if default_policy_path.exists():
                            policy_files.append(default_policy_path)
                except yaml.YAMLError:
                    pass

        # Use policies directory if nothing else specified
        if not policy_files:
            policies_dir = root / "policies"
            if policies_dir.exists():
                policy_files = list(policies_dir.glob("*.yaml"))

    engine = ValidationEngine(
        schema_path=root / "schema" / "skill_spec_v1.json",
        patterns_dir=root / "patterns",
        policy_files=policy_files if policy_files else None,
    )

    # Time the validation
    with ReportTimer() as timer:
        result = engine.validate_file(spec_path, strict=False)

    # Add evidence if requested
    evidence_report = None
    if with_evidence:
        diary_manager = DiaryManager(root)
        evidence_report = diary_manager.get_evidence_report(name)

    # Load spec data for skill info
    skill_version = "1.0.0"
    skill_owner = None
    try:
        with open(spec_path, "r", encoding="utf-8") as f:
            spec_data = yaml.safe_load(f) or {}
        skill_info = spec_data.get("skill", {})
        skill_version = skill_info.get("version", "1.0.0")
        skill_owner = skill_info.get("owner")
    except (yaml.YAMLError, IOError):
        pass

    # Handle --output-dir: generate both Markdown and JSON
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # Generate compliance report
        compliance_report = generate_compliance_report(
            validation_result=result,
            skill_name=name,
            skill_version=skill_version,
            skill_path=spec_path.parent,
            duration_ms=timer.duration_ms,
            owner=skill_owner,
        )

        # Save JSON report
        json_path = out_path / f"{name}-report.json"
        compliance_report.save(json_path, format="json")
        click.echo(f"JSON report saved: {json_path}")

        # Save Markdown report (using ComplianceReport.to_markdown)
        md_path = out_path / f"{name}-report.md"
        md_content = compliance_report.to_markdown(evidence_report)
        md_path.write_text(md_content, encoding="utf-8")
        click.echo(f"Markdown report saved: {md_path}")

        return

    if output_format == "json":
        # Generate full compliance report JSON
        compliance_report = generate_compliance_report(
            validation_result=result,
            skill_name=name,
            skill_version=skill_version,
            skill_path=spec_path.parent,
            duration_ms=timer.duration_ms,
            owner=skill_owner,
        )
        click.echo(compliance_report.to_json())
        return

    if output_format == "markdown":
        # Generate full compliance report Markdown
        compliance_report = generate_compliance_report(
            validation_result=result,
            skill_name=name,
            skill_version=skill_version,
            skill_path=spec_path.parent,
            duration_ms=timer.duration_ms,
            owner=skill_owner,
        )
        click.echo(compliance_report.to_markdown(evidence_report))
        return

    click.echo(f"Report: {name}")
    click.echo("=" * 40)
    click.echo()

    if summary or not (quality or coverage or tags or compliance or consistency):
        click.echo(result.summary())
        click.echo()

    if quality and result.quality_result:
        click.echo("Quality Analysis:")
        click.echo("-" * 40)
        for category, count in result.quality_result.category_counts.items():
            click.echo(f"  {category}: {count}")
        click.echo()

    if coverage and result.coverage_result:
        metrics = result.coverage_result.metrics
        click.echo("Coverage Analysis:")
        click.echo("-" * 40)
        click.echo(f"  Structural Coverage: {metrics.structural_score}%")
        click.echo(f"    - Failure modes covered: {metrics.failure_modes_covered}/{metrics.failure_modes_total}")
        click.echo(f"    - Rules referenced: {metrics.decision_rules_referenced}/{metrics.decision_rules_total}")
        click.echo(f"    - Inputs referenced: {metrics.inputs_referenced}/{metrics.inputs_total}")
        click.echo()
        click.echo(f"  Behavioral Coverage: {metrics.behavioral_score}%")
        click.echo(f"    - Edge cases with input: {metrics.edge_cases_with_input}/{metrics.edge_cases_total}")
        click.echo()

    if tags and result.taxonomy_result:
        click.echo("Tag Taxonomy Analysis:")
        click.echo("-" * 40)
        if result.taxonomy_result.tags_found:
            click.echo("  Tags Found:")
            for tag in result.taxonomy_result.tags_found:
                click.echo(f"    - {tag}")
        if result.taxonomy_result.policy_triggers:
            click.echo("  Policy Triggers:")
            for trigger in result.taxonomy_result.policy_triggers:
                click.echo(f"    - {trigger}")
        if result.taxonomy_result.violations:
            click.echo("  Tag Violations:")
            for v in result.taxonomy_result.violations:
                click.echo(f"    - {v.tag}: {v.message}")
        click.echo()

    if compliance and result.compliance_result:
        click.echo("Compliance Analysis:")
        click.echo("-" * 40)
        click.echo(f"  Policies Applied: {len(result.compliance_result.policies_applied)}")
        for policy in result.compliance_result.policies_applied:
            click.echo(f"    - {policy}")
        click.echo(f"  Rules Passed: {result.compliance_result.rules_passed}")
        click.echo(f"  Rules Failed: {result.compliance_result.rules_failed}")
        if result.compliance_result.violations:
            click.echo("  Violations:")
            for v in result.compliance_result.violations:
                click.echo(f"    [{v.severity}] {v.rule_id}: {v.message}")
        click.echo()

    if consistency and result.consistency_result:
        click.echo("Consistency Analysis:")
        click.echo("-" * 40)
        if result.consistency_result.issues:
            for issue in result.consistency_result.issues:
                click.echo(f"  [{issue.issue_type}] {issue.source} -> {issue.target}")
                click.echo(f"    {issue.description}")
        else:
            click.echo("  No consistency issues found.")
        click.echo()

    if with_evidence and evidence_report:
        click.echo("Evidence Summary:")
        click.echo("-" * 40)
        summary_data = evidence_report.get("summary", {})
        click.echo(f"  Total Events: {summary_data.get('total_events', 0)}")
        click.echo(f"  Test Runs: {summary_data.get('test_runs', 0)}")
        click.echo(f"  Production Runs: {summary_data.get('production_runs', 0)}")
        click.echo(f"  Success Rate: {summary_data.get('success_rate', 0):.1f}%")
        click.echo()


@cli.command("convert-report")
@click.argument("json_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output markdown file path")
def convert_report(json_path: str, output: Optional[str]):
    """Convert a JSON report to Markdown format.

    This command converts an existing JSON compliance report to human-readable
    Markdown format, useful for documentation or review purposes.

    Example:
        skillspec convert-report my-skill-report.json
        skillspec convert-report my-skill-report.json -o report.md
    """
    from .report import ComplianceReport, AuditMetadata, EvidenceTrace

    json_file = Path(json_path)

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON file: {e}", err=True)
        sys.exit(1)

    # Reconstruct ComplianceReport from JSON data
    try:
        audit_data = data.get("audit_metadata", {})
        audit_metadata = AuditMetadata(
            report_generated_at=audit_data.get("report_generated_at", ""),
            tool_version=audit_data.get("tool_version", ""),
            duration_ms=audit_data.get("duration_ms", 0),
            spec_checksum=audit_data.get("spec_checksum"),
            skill_md_checksum=audit_data.get("skill_md_checksum"),
            git_commit=audit_data.get("git_commit"),
            ci_environment=audit_data.get("ci_environment"),
        )

        evidence_data = data.get("evidence_trace", {})
        evidence_trace = EvidenceTrace(
            policies_applied=evidence_data.get("policies_applied", []),
            rules_evaluated=evidence_data.get("rules_evaluated", []),
            tags_detected=evidence_data.get("tags_detected", []),
            coverage_metrics=evidence_data.get("coverage_metrics"),
        )

        report = ComplianceReport(
            report_version=data.get("report_version", ""),
            skill=data.get("skill", {}),
            validation=data.get("validation", {}),
            evidence_trace=evidence_trace,
            audit_metadata=audit_metadata,
        )

        markdown_content = report.to_markdown()

        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown_content, encoding="utf-8")
            click.echo(f"Markdown report saved: {output_path}")
        else:
            click.echo(markdown_content)

    except KeyError as e:
        click.echo(f"Error: Invalid report structure, missing key: {e}", err=True)
        sys.exit(1)


@cli.group()
def diary():
    """Manage skill execution diary."""
    pass


@diary.command("summary")
@click.argument("name")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]),
              default="text", help="Output format")
def diary_summary(name: str, output_format: str):
    """Show diary summary for a skill."""
    root = get_skillspec_root()
    diary_manager = DiaryManager(root)

    summary = diary_manager.get_summary(name)

    if output_format == "json":
        click.echo(json.dumps(summary.to_dict(), indent=2))
    else:
        click.echo(summary.format_report())


@diary.command("prune")
@click.argument("name", required=False)
@click.option("--keep-days", default=30, help="Days of events to keep")
@click.option("--all", "prune_all", is_flag=True, help="Prune all skills")
def diary_prune(name: str, keep_days: int, prune_all: bool):
    """Prune old diary events."""
    if not name and not prune_all:
        click.echo("Error: Specify skill name or use --all", err=True)
        sys.exit(1)

    root = get_skillspec_root()
    diary_manager = DiaryManager(root)

    skill_name = None if prune_all else name
    pruned = diary_manager.prune(keep_days=keep_days, skill_name=skill_name)

    click.echo(f"Pruned {pruned} events older than {keep_days} days")


@diary.command("events")
@click.argument("name")
@click.option("--limit", default=10, help="Number of events to show")
@click.option("--type", "event_type", type=click.Choice(["test_run", "production_execution"]),
              help="Filter by event type")
def diary_events(name: str, limit: int, event_type: str):
    """List recent diary events for a skill."""
    root = get_skillspec_root()
    diary_manager = DiaryManager(root)

    events = list(diary_manager.read_events(skill_name=name, event_type=event_type))
    events = sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]

    if not events:
        click.echo(f"No events found for skill '{name}'")
        return

    click.echo(f"Recent events for {name}:")
    click.echo()

    for event in events:
        status = "OK" if event.success else "FAIL"
        color = "green" if event.success else "red"
        click.secho(f"  [{status}] ", fg=color, nl=False)
        click.echo(f"{event.event_type} at {event.timestamp} ({event.duration_ms}ms)")
        if event.error:
            click.echo(f"        Error: {event.error[:60]}")


@diary.command("init")
def diary_init():
    """Initialize diary system and gitignore."""
    root = get_skillspec_root()
    diary_manager = DiaryManager(root)
    diary_manager.ensure_dirs()

    # Also add .skillspec to gitignore
    project_root = root.parent
    ensure_gitignore(project_root)

    click.echo("Diary system initialized.")
    click.echo(f"  Diary directory: {diary_manager.diary_dir}")
    click.echo(f"  Traces directory: {diary_manager.traces_dir}")
    click.echo("  Added .skillspec/ to .gitignore")


@cli.command()
@click.argument("skill_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output spec.yaml path")
@click.option("--force", is_flag=True, help="Overwrite existing spec.yaml")
@click.option("--format", "output_format", type=click.Choice(["yaml", "json"]),
              default="yaml", help="Output format")
def migrate(skill_path: str, output: str, force: bool, output_format: str):
    """Migrate an existing SKILL.md to spec.yaml format."""
    skill_md_path = Path(skill_path)

    # Determine if path is a file or directory
    if skill_md_path.is_dir():
        skill_md_path = skill_md_path / "SKILL.md"

    if not skill_md_path.exists():
        click.echo(f"Error: SKILL.md not found at {skill_md_path}", err=True)
        sys.exit(1)

    # Determine output path
    if output:
        output_path = Path(output)
    else:
        output_path = skill_md_path.parent / "spec.yaml"

    if output_path.exists() and not force:
        click.echo(f"Error: {output_path} already exists. Use --force to overwrite.",
                  err=True)
        sys.exit(1)

    # Run migration
    click.echo(f"Migrating: {skill_md_path}")
    result = migrate_skill(skill_md_path)

    if not result.success:
        click.echo("Migration failed:", err=True)
        for warning in result.warnings:
            click.echo(f"  - {warning}", err=True)
        sys.exit(1)

    # Write output
    if output_format == "json":
        content = json.dumps(result.spec_data, indent=2)
        output_path = output_path.with_suffix(".json") if output_path.suffix == ".yaml" else output_path
    else:
        content = yaml.dump(result.spec_data, default_flow_style=False, allow_unicode=True, sort_keys=False)

    output_path.write_text(content, encoding="utf-8")

    click.echo(f"Generated: {output_path}")
    click.echo()

    # Show guide
    click.echo(result.guide)

    # Show todo count
    if result.todos:
        click.secho(f"\nFound {len(result.todos)} items requiring attention.", fg="yellow")


# =============================================================================
# Deployment Commands
# =============================================================================


@cli.group()
def deploy():
    """Deployment commands for skills."""
    pass


@deploy.command("bundle")
@click.argument("name")
@click.option("--output-dir", "-o", type=click.Path(), help="Output directory for bundle")
@click.option("--include-optional", is_flag=True, help="Include tests and examples")
def deploy_bundle(name: str, output_dir: Optional[str], include_optional: bool):
    """Create a deployment bundle for a skill."""
    from .deploy import BundleCreator

    spec_path = find_skill(name)

    if not spec_path:
        click.echo(f"Error: Skill '{name}' not found", err=True)
        sys.exit(1)

    skill_dir = spec_path.parent
    root = get_skillspec_root()

    # Determine output directory
    if output_dir:
        out_path = Path(output_dir)
    else:
        out_path = root / "bundles"

    out_path.mkdir(parents=True, exist_ok=True)
    bundle_path = out_path / f"{name}-bundle.zip"

    # Create bundle
    creator = BundleCreator(skill_dir)
    bundle = creator.create_bundle(bundle_path, include_optional)

    click.echo(f"Bundle created: {bundle_path}")
    click.echo(f"  Skill: {bundle.skill_name}")
    click.echo(f"  Version: {bundle.version}")
    click.echo(f"  Files: {len(bundle.files)}")
    click.echo(f"  Checksum: {bundle.checksum}")
    click.echo()
    click.echo(f"Manifest: {bundle_path.with_suffix('.manifest.json')}")


@deploy.command("preflight")
@click.argument("name")
@click.option("--target", "-t", help="Target to check against")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]),
              default="text", help="Output format")
def deploy_preflight(name: str, target: Optional[str], output_format: str):
    """Run pre-flight checks before deployment."""
    from .deploy import PreflightChecker, TargetRegistry

    spec_path = find_skill(name)

    if not spec_path:
        click.echo(f"Error: Skill '{name}' not found", err=True)
        sys.exit(1)

    skill_dir = spec_path.parent
    root = get_skillspec_root()

    # Load target if specified
    deployment_target = None
    if target:
        registry = TargetRegistry(root / "targets.yaml")
        deployment_target = registry.get_target(target)
        if not deployment_target:
            click.echo(f"Error: Target '{target}' not found", err=True)
            sys.exit(1)

    # Create validation engine
    engine = ValidationEngine(
        schema_path=root / "schema" / "skill_spec_v1.json",
        patterns_dir=root / "patterns",
    )

    # Run checks
    checker = PreflightChecker(skill_dir, engine)
    result = checker.run_checks(deployment_target)

    if output_format == "json":
        click.echo(json.dumps(result.to_dict(), indent=2))
    else:
        status = "PASSED" if result.success else "FAILED"
        color = "green" if result.success else "red"

        click.echo()
        click.secho(f"Pre-flight Check: {status}", fg=color, bold=True)
        if result.target:
            click.echo(f"Target: {result.target}")
        click.echo()

        for check in result.checks:
            check_status = "OK" if check.passed else "FAIL"
            check_color = "green" if check.passed else ("red" if check.severity == "error" else "yellow")
            click.secho(f"  [{check_status}] ", fg=check_color, nl=False)
            click.echo(f"{check.name}: {check.message}")

    sys.exit(0 if result.success else 1)


@deploy.command("target")
@click.argument("action", type=click.Choice(["list", "add", "remove"]))
@click.argument("name", required=False)
@click.option("--url", help="Target URL (for add)")
@click.option("--auth", "auth_type", type=click.Choice(["none", "api_key", "oauth"]),
              default="none", help="Authentication type")
@click.option("--env-var", help="Environment variable for credentials")
@click.option("--description", help="Target description")
def deploy_target(action: str, name: Optional[str], url: Optional[str],
                  auth_type: str, env_var: Optional[str], description: Optional[str]):
    """Manage deployment targets."""
    from .deploy import TargetRegistry, DeploymentTarget

    root = get_skillspec_root()
    registry = TargetRegistry(root / "targets.yaml")

    if action == "list":
        targets = registry.list_targets()
        if not targets:
            click.echo("No targets configured.")
            click.echo("Add one with: skillspec deploy target add <name> --url <url>")
            return

        click.echo("Deployment Targets:")
        click.echo()
        for t in targets:
            click.echo(f"  {t.name}")
            click.echo(f"    URL: {t.url}")
            click.echo(f"    Auth: {t.auth_type}")
            if t.env_var:
                click.echo(f"    Env: ${t.env_var}")
            if t.description:
                click.echo(f"    Description: {t.description}")
            click.echo()

    elif action == "add":
        if not name:
            click.echo("Error: Name is required for 'add'", err=True)
            sys.exit(1)
        if not url:
            click.echo("Error: --url is required for 'add'", err=True)
            sys.exit(1)

        target = DeploymentTarget(
            name=name,
            url=url,
            auth_type=auth_type,
            env_var=env_var,
            description=description or "",
        )
        registry.add_target(target)
        click.echo(f"Added target: {name}")

    elif action == "remove":
        if not name:
            click.echo("Error: Name is required for 'remove'", err=True)
            sys.exit(1)

        if registry.remove_target(name):
            click.echo(f"Removed target: {name}")
        else:
            click.echo(f"Error: Target '{name}' not found", err=True)
            sys.exit(1)


@deploy.command("status")
@click.argument("name")
def deploy_status(name: str):
    """Show deployment status for a skill."""
    spec_path = find_skill(name)

    if not spec_path:
        click.echo(f"Error: Skill '{name}' not found", err=True)
        sys.exit(1)

    skill_dir = spec_path.parent
    root = get_skillspec_root()

    click.echo(f"Deployment Status: {name}")
    click.echo("=" * 40)
    click.echo()

    # Check if SKILL.md exists
    skill_md = skill_dir / "SKILL.md"
    click.echo(f"  spec.yaml: {'OK' if spec_path.exists() else 'MISSING'}")
    click.echo(f"  SKILL.md: {'OK' if skill_md.exists() else 'MISSING'}")
    click.echo()

    # Check for bundles
    bundles_dir = root / "bundles"
    bundle_path = bundles_dir / f"{name}-bundle.zip"
    if bundle_path.exists():
        manifest_path = bundle_path.with_suffix(".manifest.json")
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            click.echo("Latest Bundle:")
            click.echo(f"  Version: {manifest.get('version', 'unknown')}")
            click.echo(f"  Created: {manifest.get('created_at', 'unknown')}")
            click.echo(f"  Checksum: {manifest.get('checksum', 'unknown')}")
        else:
            click.echo("Latest Bundle: exists (no manifest)")
    else:
        click.echo("Latest Bundle: none")


# =============================================================================
# Schema Documentation Commands
# =============================================================================

SCHEMA_SECTIONS = {
    "skill": {
        "description": "Skill metadata - identity and classification",
        "required": True,
        "fields": {
            "name": ("string", "Kebab-case name, e.g., 'extract-api-contract'"),
            "version": ("string", "Semantic version, e.g., '1.0.0'"),
            "purpose": ("string", "Single sentence describing what this skill does"),
            "owner": ("string", "Team or individual responsible"),
            "category": ("string", "NEW v1.1: documentation|analysis|generation|transformation|validation|orchestration"),
            "complexity": ("string", "NEW v1.1: low|standard|advanced"),
            "tools_required": ("array", "NEW v1.1: Claude Code tools needed (Read, Write, Grep, etc.)"),
            "personas": ("array", "NEW v1.1: Roles that benefit (developer, architect, etc.)"),
        },
    },
    "triggers": {
        "description": "NEW v1.1: When to activate this skill (Superpowers-style)",
        "required": False,
        "source": "Superpowers",
        "fields": {
            "use_when": ("array", "Conditions that should trigger this skill"),
            "do_not_use_when": ("array", "Conditions when NOT to use this skill"),
        },
    },
    "inputs": {
        "description": "Input contract - what the skill accepts",
        "required": True,
        "fields": {
            "name": ("string", "Input parameter name"),
            "type": ("string", "string|number|boolean|object|array"),
            "required": ("boolean", "Whether input is mandatory"),
            "constraints": ("array", "Validation rules (not_empty, max_length, etc.)"),
            "domain": ("object", "Value domain (enum, range, pattern_set, any)"),
            "description": ("string", "Precise semantic definition"),
            "tags": ("array", "Classification tags (content:code, sensitive:pii, etc.)"),
        },
    },
    "preconditions": {
        "description": "Prerequisites - what must be true before running",
        "required": True,
        "fields": {},
    },
    "non_goals": {
        "description": "Explicit boundaries - what this skill does NOT do",
        "required": True,
        "fields": {},
    },
    "boundaries": {
        "description": "NEW v1.1: Clear will/will_not declarations (SuperClaude-style)",
        "required": False,
        "source": "SuperClaude",
        "fields": {
            "will": ("array", "Explicit capabilities this skill provides"),
            "will_not": ("array", "Explicit limitations and exclusions"),
        },
    },
    "decision_rules": {
        "description": "Decision logic - explicit conditional behavior",
        "required": True,
        "fields": {
            "_config.match_strategy": ("string", "first_match|priority|all_match"),
            "_config.conflict_resolution": ("string", "error|warn|first_wins"),
            "rules[].id": ("string", "Unique rule identifier"),
            "rules[].priority": ("number", "Rule priority (higher = first)"),
            "rules[].when": ("string", "Condition expression"),
            "rules[].then": ("object", "Action when condition matches"),
            "rules[].is_default": ("boolean", "Default rule if no others match"),
        },
    },
    "steps": {
        "description": "Execution flow - technical step-by-step",
        "required": True,
        "fields": {
            "id": ("string", "Step identifier"),
            "action": ("string", "What this step does"),
            "output": ("string", "Output variable name"),
            "based_on": ("array", "Input dependencies"),
            "condition": ("string", "Optional execution condition"),
        },
    },
    "behavioral_flow": {
        "description": "NEW v1.1: High-level behavioral phases (SuperClaude-style)",
        "required": False,
        "source": "SuperClaude",
        "fields": {
            "phase": ("string", "Phase name (analyze, generate, validate, etc.)"),
            "description": ("string", "What happens in this phase"),
            "key_actions": ("array", "Key actions in this phase"),
        },
    },
    "output_contract": {
        "description": "Output schema - what the skill produces",
        "required": True,
        "fields": {
            "format": ("string", "json|text|markdown|yaml"),
            "schema": ("object", "JSON Schema for output validation"),
        },
    },
    "failure_modes": {
        "description": "Error handling - known failure conditions",
        "required": True,
        "fields": {
            "code": ("string", "Error code identifier"),
            "retryable": ("boolean", "Whether operation can be retried"),
            "description": ("string", "When and why this failure occurs"),
        },
    },
    "edge_cases": {
        "description": "Boundary conditions - edge case coverage",
        "required": True,
        "fields": {
            "case": ("string", "Edge case name"),
            "description": ("string", "Edge case description"),
            "input": ("object", "Sample input triggering this case"),
            "expected": ("object", "Expected output/behavior"),
        },
    },
    "anti_patterns": {
        "description": "NEW v1.1: Common mistakes and rationalizations (Superpowers-style)",
        "required": False,
        "source": "Superpowers",
        "fields": {
            "mistakes": ("array", "Common mistakes: pattern, why_bad, correct"),
            "rationalizations": ("array", "Excuses AI might use: excuse, reality"),
            "red_flags": ("array", "Warning signs that skill is being misused"),
        },
    },
    "context": {
        "description": "Collaboration info - related skills and scenarios",
        "required": False,
        "fields": {
            "works_with": ("array", "Related skills: skill, reason"),
            "prerequisites": ("array", "What user needs to do first"),
            "scenarios": ("array", "Typical usage scenarios: name, trigger, description"),
        },
    },
    "examples": {
        "description": "Usage examples - concrete demonstrations",
        "required": False,
        "fields": {
            "name": ("string", "Example name"),
            "scenario": ("string", "NEW v1.1: Context/scenario description"),
            "trigger": ("string", "NEW v1.1: How user triggers this"),
            "input": ("object", "Example input"),
            "output": ("object", "Expected output"),
            "explanation": ("string", "What happens in this example"),
        },
    },
    "_meta": {
        "description": "Meta configuration - spec behavior settings",
        "required": False,
        "fields": {
            "content_language": ("string", "en|zh|auto"),
            "mixed_language_strategy": ("string", "union|segment_detect|primary"),
            "format": ("string", "NEW v1.1: full|minimal"),
            "token_budget": ("number", "NEW v1.1: Target word count for SKILL.md"),
        },
    },
}


@cli.command("schema")
@click.argument("section", required=False)
@click.option("--new-only", is_flag=True, help="Show only v1.1 new sections")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]),
              default="text", help="Output format")
def schema_docs(section: Optional[str], new_only: bool, output_format: str):
    """Show schema documentation for spec.yaml fields.

    Display all sections or a specific section's fields and descriptions.

    \b
    Examples:
        skillspec schema              # Show all sections
        skillspec schema skill        # Show 'skill' section fields
        skillspec schema triggers     # Show 'triggers' section fields
        skillspec schema --new-only   # Show only v1.1 new sections

    \b
    v1.1 New Sections:
        triggers       - When to activate (Superpowers-style)
        boundaries     - Will/will_not declarations (SuperClaude-style)
        anti_patterns  - Mistakes and rationalizations (Superpowers-style)
        behavioral_flow - High-level phases (SuperClaude-style)
    """
    if output_format == "json":
        if section:
            if section in SCHEMA_SECTIONS:
                click.echo(json.dumps({section: SCHEMA_SECTIONS[section]}, indent=2))
            else:
                click.echo(f'{{"error": "Unknown section: {section}"}}')
                sys.exit(1)
        else:
            data = SCHEMA_SECTIONS
            if new_only:
                data = {k: v for k, v in data.items() if v.get("source") or "NEW v1.1" in v.get("description", "")}
            click.echo(json.dumps(data, indent=2))
        return

    # Text format
    if section:
        if section not in SCHEMA_SECTIONS:
            click.echo(f"Error: Unknown section '{section}'", err=True)
            click.echo(f"Available sections: {', '.join(SCHEMA_SECTIONS.keys())}", err=True)
            sys.exit(1)

        _print_section(section, SCHEMA_SECTIONS[section])
    else:
        click.echo("Skill-Spec Schema v1.1")
        click.echo("=" * 60)
        click.echo()

        if new_only:
            click.secho("v1.1 New Sections:", fg="cyan", bold=True)
            click.echo()

        for name, info in SCHEMA_SECTIONS.items():
            is_new = info.get("source") or "NEW v1.1" in info.get("description", "")
            if new_only and not is_new:
                continue
            _print_section_brief(name, info)

        if not new_only:
            click.echo()
            click.echo("Use 'skillspec schema <section>' for detailed field info")
            click.echo("Use 'skillspec schema --new-only' to see v1.1 additions")


def _print_section(name: str, info: dict) -> None:
    """Print detailed section info."""
    is_new = info.get("source") or "NEW v1.1" in info.get("description", "")
    required_text = "required" if info.get("required") else "optional"
    source_text = f" (from {info['source']})" if info.get("source") else ""

    click.echo()
    if is_new:
        click.secho(f"[{name}]", fg="cyan", bold=True)
    else:
        click.secho(f"[{name}]", bold=True)

    click.echo(f"  {info['description']}")
    click.echo(f"  Status: {required_text}{source_text}")
    click.echo()

    if info.get("fields"):
        click.echo("  Fields:")
        for field_name, (field_type, field_desc) in info["fields"].items():
            is_field_new = "NEW v1.1" in field_desc
            if is_field_new:
                click.secho(f"    {field_name}", fg="cyan", nl=False)
                click.echo(f" ({field_type})")
                click.echo(f"      {field_desc}")
            else:
                click.echo(f"    {field_name} ({field_type})")
                click.echo(f"      {field_desc}")
    else:
        click.echo("  (array of strings)")


def _print_section_brief(name: str, info: dict) -> None:
    """Print brief section info."""
    is_new = info.get("source") or "NEW v1.1" in info.get("description", "")
    required_marker = "*" if info.get("required") else " "
    source_text = f" [{info['source']}]" if info.get("source") else ""

    if is_new:
        click.secho(f"  {required_marker} {name}", fg="cyan", nl=False)
        click.echo(f"{source_text}")
        click.echo(f"      {info['description']}")
    else:
        click.echo(f"  {required_marker} {name}")
        click.echo(f"      {info['description']}")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
