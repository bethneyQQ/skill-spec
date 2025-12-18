"""
SKILL.md Preservation Protocol.

Handles generated vs manual block markers and preservation during regeneration.
This ensures that manually edited content is not lost when regenerating SKILL.md.

Block Markers:
- <!-- skillspec:generated:start --> ... <!-- skillspec:generated:end -->
  Content that can be regenerated from spec.yaml

- <!-- skillspec:manual:start --> ... <!-- skillspec:manual:end -->
  Content that must be preserved during regeneration
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class BlockType(Enum):
    """Type of content block."""
    GENERATED = "generated"
    MANUAL = "manual"
    UNMARKED = "unmarked"


# Block marker patterns
GENERATED_START = "<!-- skillspec:generated:start -->"
GENERATED_END = "<!-- skillspec:generated:end -->"
MANUAL_START = "<!-- skillspec:manual:start -->"
MANUAL_END = "<!-- skillspec:manual:end -->"

# Regex patterns for extracting blocks
GENERATED_PATTERN = re.compile(
    r'<!-- skillspec:generated:start -->\n?(.*?)<!-- skillspec:generated:end -->',
    re.DOTALL
)
MANUAL_PATTERN = re.compile(
    r'<!-- skillspec:manual:start -->\n?(.*?)<!-- skillspec:manual:end -->',
    re.DOTALL
)


@dataclass
class ContentBlock:
    """Represents a block of content in SKILL.md."""

    block_type: BlockType
    content: str
    section_name: Optional[str] = None  # e.g., "Purpose", "Custom Notes"
    checksum: Optional[str] = None  # For generated blocks, to detect changes
    start_line: int = 0
    end_line: int = 0

    def compute_checksum(self) -> str:
        """Compute MD5 checksum of content."""
        return hashlib.md5(self.content.encode('utf-8')).hexdigest()[:8]


@dataclass
class ParsedDocument:
    """Parsed SKILL.md document with blocks extracted."""

    blocks: list[ContentBlock] = field(default_factory=list)
    raw_content: str = ""
    has_markers: bool = False

    def get_manual_blocks(self) -> list[ContentBlock]:
        """Get all manual blocks."""
        return [b for b in self.blocks if b.block_type == BlockType.MANUAL]

    def get_generated_blocks(self) -> list[ContentBlock]:
        """Get all generated blocks."""
        return [b for b in self.blocks if b.block_type == BlockType.GENERATED]

    def get_manual_block_by_section(self, section_name: str) -> Optional[ContentBlock]:
        """Get manual block for a specific section."""
        for block in self.blocks:
            if block.block_type == BlockType.MANUAL and block.section_name == section_name:
                return block
        return None


@dataclass
class PreservationResult:
    """Result of preservation operation."""

    success: bool
    merged_content: str
    manual_blocks_preserved: int = 0
    generated_blocks_updated: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_skill_md(content: str) -> ParsedDocument:
    """
    Parse SKILL.md content and extract blocks.

    Args:
        content: Raw SKILL.md content

    Returns:
        ParsedDocument with blocks extracted
    """
    doc = ParsedDocument(raw_content=content)

    # Check if document has any markers
    has_generated = GENERATED_START in content
    has_manual = MANUAL_START in content
    doc.has_markers = has_generated or has_manual

    if not doc.has_markers:
        # No markers - treat entire content as unmarked
        doc.blocks.append(ContentBlock(
            block_type=BlockType.UNMARKED,
            content=content
        ))
        return doc

    # Parse content line by line to preserve structure
    lines = content.split('\n')
    current_block_lines = []
    current_block_type = BlockType.UNMARKED
    current_section = None

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check for block start markers
        if GENERATED_START in line:
            # Save previous block if any
            if current_block_lines:
                doc.blocks.append(ContentBlock(
                    block_type=current_block_type,
                    content='\n'.join(current_block_lines),
                    section_name=current_section
                ))
                current_block_lines = []

            current_block_type = BlockType.GENERATED
            i += 1
            continue

        elif MANUAL_START in line:
            # Save previous block if any
            if current_block_lines:
                doc.blocks.append(ContentBlock(
                    block_type=current_block_type,
                    content='\n'.join(current_block_lines),
                    section_name=current_section
                ))
                current_block_lines = []

            current_block_type = BlockType.MANUAL
            i += 1
            continue

        # Check for block end markers
        elif GENERATED_END in line or MANUAL_END in line:
            # Save current block
            doc.blocks.append(ContentBlock(
                block_type=current_block_type,
                content='\n'.join(current_block_lines),
                section_name=current_section
            ))
            current_block_lines = []
            current_block_type = BlockType.UNMARKED
            i += 1
            continue

        # Track section headers for context
        if line.startswith('## '):
            current_section = line[3:].strip()
        elif line.startswith('# '):
            current_section = line[2:].strip()

        current_block_lines.append(line)
        i += 1

    # Save any remaining content
    if current_block_lines:
        doc.blocks.append(ContentBlock(
            block_type=current_block_type,
            content='\n'.join(current_block_lines),
            section_name=current_section
        ))

    return doc


def wrap_generated_block(content: str, section_name: Optional[str] = None) -> str:
    """
    Wrap content in generated block markers.

    Frontmatter (--- ... ---) is kept outside the markers because:
    1. It must be at the very start of the file for proper parsing
    2. It contains skill metadata that should be visible to parsers

    Args:
        content: Content to wrap
        section_name: Optional section name for context

    Returns:
        Content wrapped in markers, with frontmatter outside if present
    """
    # Check for YAML frontmatter at the start (--- ... ---)
    frontmatter_pattern = re.compile(r'^(---\s*\n.*?\n---\s*\n)', re.DOTALL)
    frontmatter_match = frontmatter_pattern.match(content)

    if frontmatter_match:
        # Extract frontmatter and remaining content
        frontmatter = frontmatter_match.group(1)
        remaining_content = content[frontmatter_match.end():]
        # Frontmatter goes outside, rest inside generated block
        return f"{frontmatter}{GENERATED_START}\n{remaining_content}\n{GENERATED_END}"
    else:
        # No frontmatter, wrap everything
        return f"{GENERATED_START}\n{content}\n{GENERATED_END}"


def wrap_manual_block(content: str, section_name: Optional[str] = None) -> str:
    """
    Wrap content in manual block markers.

    Args:
        content: Content to wrap
        section_name: Optional section name for context

    Returns:
        Content wrapped in markers
    """
    return f"{MANUAL_START}\n{content}\n{MANUAL_END}"


def merge_with_preservation(
    existing_content: str,
    new_generated_content: str,
    force: bool = False
) -> PreservationResult:
    """
    Merge new generated content with existing content, preserving manual blocks.

    Args:
        existing_content: Current SKILL.md content
        new_generated_content: Newly generated content from spec.yaml
        force: If True, overwrite everything including manual blocks

    Returns:
        PreservationResult with merged content
    """
    result = PreservationResult(success=True, merged_content="")

    # If force mode, just return new content with markers
    if force:
        result.merged_content = new_generated_content
        result.warnings.append("Force mode: all existing content replaced")
        return result

    # Parse existing document
    existing_doc = parse_skill_md(existing_content)

    # If no markers in existing content, wrap new content in generated markers
    if not existing_doc.has_markers:
        result.merged_content = wrap_generated_block(new_generated_content)
        result.warnings.append("No markers found in existing content - wrapped new content in generated markers")
        return result

    # Get manual blocks to preserve
    manual_blocks = existing_doc.get_manual_blocks()
    result.manual_blocks_preserved = len(manual_blocks)

    # Parse new content to get section structure
    new_doc = parse_skill_md(new_generated_content)

    # Build merged content
    merged_lines = []

    # Check for frontmatter in new content - it should be outside markers
    frontmatter_pattern = re.compile(r'^(---\s*\n.*?\n---\s*\n)', re.DOTALL)
    frontmatter_match = frontmatter_pattern.match(new_generated_content)

    if frontmatter_match:
        # Add frontmatter outside markers
        frontmatter = frontmatter_match.group(1).strip()
        remaining_content = new_generated_content[frontmatter_match.end():]
        merged_lines.append(frontmatter)
        merged_lines.append("")
        merged_lines.append(GENERATED_START)
        merged_lines.append(remaining_content.strip())
        merged_lines.append(GENERATED_END)
    else:
        # No frontmatter, wrap everything
        merged_lines.append(GENERATED_START)
        merged_lines.append(new_generated_content.strip())
        merged_lines.append(GENERATED_END)

    result.generated_blocks_updated = 1

    # Append preserved manual blocks
    for manual_block in manual_blocks:
        merged_lines.append("")  # Blank line separator
        merged_lines.append(MANUAL_START)
        merged_lines.append(manual_block.content.strip())
        merged_lines.append(MANUAL_END)

    result.merged_content = '\n'.join(merged_lines)
    return result


def extract_manual_blocks(content: str) -> list[ContentBlock]:
    """
    Extract all manual blocks from SKILL.md content.

    Args:
        content: SKILL.md content

    Returns:
        List of manual ContentBlocks
    """
    doc = parse_skill_md(content)
    return doc.get_manual_blocks()


def extract_generated_blocks(content: str) -> list[ContentBlock]:
    """
    Extract all generated blocks from SKILL.md content.

    Args:
        content: SKILL.md content

    Returns:
        List of generated ContentBlocks
    """
    doc = parse_skill_md(content)
    return doc.get_generated_blocks()


def validate_generated_block_consistency(
    generated_block: ContentBlock,
    spec_generated: str
) -> tuple[bool, Optional[str]]:
    """
    Validate that a generated block can be reproduced from spec.

    Args:
        generated_block: Existing generated block
        spec_generated: Content generated from current spec

    Returns:
        Tuple of (is_consistent, difference_description)
    """
    # Normalize whitespace for comparison
    existing_normalized = ' '.join(generated_block.content.split())
    spec_normalized = ' '.join(spec_generated.split())

    if existing_normalized == spec_normalized:
        return True, None

    # Find specific differences
    existing_lines = set(generated_block.content.strip().split('\n'))
    spec_lines = set(spec_generated.strip().split('\n'))

    added = spec_lines - existing_lines
    removed = existing_lines - spec_lines

    diff_desc = []
    if added:
        diff_desc.append(f"Lines added from spec: {len(added)}")
    if removed:
        diff_desc.append(f"Lines removed from existing: {len(removed)}")

    return False, "; ".join(diff_desc) if diff_desc else "Content differs"


@dataclass
class ConsistencyValidationResult:
    """Result of generated block consistency validation."""

    valid: bool
    blocks_checked: int = 0
    inconsistencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "blocks_checked": self.blocks_checked,
            "inconsistencies": self.inconsistencies
        }


def validate_document_consistency(
    skill_md_content: str,
    spec_generated_content: str
) -> ConsistencyValidationResult:
    """
    Validate that generated blocks in SKILL.md can be reproduced from spec.

    Args:
        skill_md_content: Current SKILL.md content
        spec_generated_content: Content that would be generated from spec

    Returns:
        ConsistencyValidationResult
    """
    result = ConsistencyValidationResult(valid=True)

    doc = parse_skill_md(skill_md_content)
    generated_blocks = doc.get_generated_blocks()

    result.blocks_checked = len(generated_blocks)

    if not generated_blocks:
        # No generated blocks to check
        return result

    for i, block in enumerate(generated_blocks):
        is_consistent, diff = validate_generated_block_consistency(
            block, spec_generated_content
        )
        if not is_consistent:
            result.valid = False
            result.inconsistencies.append(
                f"Generated block {i+1}: {diff}"
            )

    return result


def add_preservation_markers(content: str) -> str:
    """
    Add preservation markers to unmarked SKILL.md content.

    This wraps the entire content in generated markers, making it
    ready for the preservation protocol.

    Args:
        content: Unmarked SKILL.md content

    Returns:
        Content with generated markers
    """
    doc = parse_skill_md(content)

    if doc.has_markers:
        return content  # Already has markers

    return wrap_generated_block(content)


def insert_manual_section(
    content: str,
    manual_content: str,
    after_section: Optional[str] = None
) -> str:
    """
    Insert a manual section into SKILL.md content.

    Args:
        content: Current SKILL.md content
        manual_content: Manual content to insert
        after_section: Section name after which to insert (optional)

    Returns:
        Content with manual section inserted
    """
    doc = parse_skill_md(content)

    # If we have markers and a target section, insert after it
    if after_section:
        lines = content.split('\n')
        insert_idx = len(lines)

        for i, line in enumerate(lines):
            if line.startswith(f'## {after_section}'):
                # Find end of this section (next ## or end)
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith('## ') or lines[j].startswith('# '):
                        insert_idx = j
                        break
                else:
                    insert_idx = len(lines)
                break

        # Insert manual block
        manual_block = [
            "",
            MANUAL_START,
            manual_content.strip(),
            MANUAL_END,
            ""
        ]

        new_lines = lines[:insert_idx] + manual_block + lines[insert_idx:]
        return '\n'.join(new_lines)

    # Default: append at end
    return content.rstrip() + '\n\n' + wrap_manual_block(manual_content) + '\n'
