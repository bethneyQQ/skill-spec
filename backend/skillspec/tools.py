"""
Standard Tool Registry for Skill-Spec.

This module defines the standard tools available in Claude Code and other
AI agent environments. Tools are organized by category and include
parameter definitions for validation.

Usage:
    from skillspec.tools import STANDARD_TOOLS, get_tool, validate_tool_binding

    # Get a tool definition
    read_tool = get_tool("Read")

    # Validate a tool binding in a step
    errors = validate_tool_binding(tool_binding, available_tools)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ToolCategory(str, Enum):
    """Categories for organizing tools."""
    FILE_SYSTEM = "file_system"
    SEARCH = "search"
    EXECUTION = "execution"
    WEB = "web"
    INTERACTION = "interaction"
    NOTEBOOK = "notebook"
    MCP = "mcp"


@dataclass
class StandardToolParam:
    """Parameter definition for a standard tool."""
    name: str
    type: str  # string, number, boolean, object, array
    required: bool = False
    description: str = ""
    default: Any = None


@dataclass
class StandardTool:
    """Definition of a standard tool available in Claude Code."""
    name: str
    category: ToolCategory
    description: str
    params: List[StandardToolParam] = field(default_factory=list)
    returns: str = ""
    requires_approval: bool = False
    sandbox_safe: bool = True
    aliases: List[str] = field(default_factory=list)


# Standard Claude Code Tools
STANDARD_TOOLS: Dict[str, StandardTool] = {
    # === File System Tools ===
    "Read": StandardTool(
        name="Read",
        category=ToolCategory.FILE_SYSTEM,
        description="Read contents of a file from the local filesystem",
        params=[
            StandardToolParam("file_path", "string", True, "Absolute path to the file"),
            StandardToolParam("offset", "number", False, "Line number to start reading from"),
            StandardToolParam("limit", "number", False, "Number of lines to read"),
        ],
        returns="File contents with line numbers",
        requires_approval=False,
        sandbox_safe=True,
    ),

    "Write": StandardTool(
        name="Write",
        category=ToolCategory.FILE_SYSTEM,
        description="Write content to a file, creating or overwriting",
        params=[
            StandardToolParam("file_path", "string", True, "Absolute path to the file"),
            StandardToolParam("content", "string", True, "Content to write"),
        ],
        returns="Success confirmation",
        requires_approval=True,
        sandbox_safe=True,
    ),

    "Edit": StandardTool(
        name="Edit",
        category=ToolCategory.FILE_SYSTEM,
        description="Perform exact string replacements in a file",
        params=[
            StandardToolParam("file_path", "string", True, "Absolute path to the file"),
            StandardToolParam("old_string", "string", True, "Text to replace"),
            StandardToolParam("new_string", "string", True, "Replacement text"),
            StandardToolParam("replace_all", "boolean", False, "Replace all occurrences", False),
        ],
        returns="Updated file contents",
        requires_approval=True,
        sandbox_safe=True,
    ),

    # === Search Tools ===
    "Glob": StandardTool(
        name="Glob",
        category=ToolCategory.SEARCH,
        description="Find files matching a glob pattern",
        params=[
            StandardToolParam("pattern", "string", True, "Glob pattern (e.g., '**/*.py')"),
            StandardToolParam("path", "string", False, "Directory to search in"),
        ],
        returns="List of matching file paths",
        requires_approval=False,
        sandbox_safe=True,
    ),

    "Grep": StandardTool(
        name="Grep",
        category=ToolCategory.SEARCH,
        description="Search file contents using regex patterns",
        params=[
            StandardToolParam("pattern", "string", True, "Regex pattern to search"),
            StandardToolParam("path", "string", False, "File or directory to search"),
            StandardToolParam("glob", "string", False, "Filter files by glob pattern"),
            StandardToolParam("output_mode", "string", False, "content, files_with_matches, or count"),
        ],
        returns="Search results",
        requires_approval=False,
        sandbox_safe=True,
    ),

    # === Execution Tools ===
    "Bash": StandardTool(
        name="Bash",
        category=ToolCategory.EXECUTION,
        description="Execute shell commands",
        params=[
            StandardToolParam("command", "string", True, "Command to execute"),
            StandardToolParam("timeout", "number", False, "Timeout in milliseconds"),
            StandardToolParam("description", "string", False, "Description of what this command does"),
        ],
        returns="Command output (stdout/stderr)",
        requires_approval=True,
        sandbox_safe=False,
        aliases=["Shell", "Command"],
    ),

    "Task": StandardTool(
        name="Task",
        category=ToolCategory.EXECUTION,
        description="Launch a sub-agent to handle complex tasks",
        params=[
            StandardToolParam("prompt", "string", True, "Task description for the agent"),
            StandardToolParam("subagent_type", "string", True, "Type of agent to use"),
            StandardToolParam("description", "string", True, "Short description of the task"),
        ],
        returns="Agent execution result",
        requires_approval=False,
        sandbox_safe=True,
    ),

    # === Web Tools ===
    "WebFetch": StandardTool(
        name="WebFetch",
        category=ToolCategory.WEB,
        description="Fetch and process content from a URL",
        params=[
            StandardToolParam("url", "string", True, "URL to fetch"),
            StandardToolParam("prompt", "string", True, "Prompt to process the content"),
        ],
        returns="Processed web content",
        requires_approval=False,
        sandbox_safe=True,
    ),

    "WebSearch": StandardTool(
        name="WebSearch",
        category=ToolCategory.WEB,
        description="Search the web and return results",
        params=[
            StandardToolParam("query", "string", True, "Search query"),
            StandardToolParam("allowed_domains", "array", False, "Domains to include"),
            StandardToolParam("blocked_domains", "array", False, "Domains to exclude"),
        ],
        returns="Search results with links",
        requires_approval=False,
        sandbox_safe=True,
    ),

    # === Interaction Tools ===
    "AskUserQuestion": StandardTool(
        name="AskUserQuestion",
        category=ToolCategory.INTERACTION,
        description="Ask the user a question with options",
        params=[
            StandardToolParam("questions", "array", True, "Questions with options"),
        ],
        returns="User's answers",
        requires_approval=False,
        sandbox_safe=True,
    ),

    "TodoWrite": StandardTool(
        name="TodoWrite",
        category=ToolCategory.INTERACTION,
        description="Manage a structured task list",
        params=[
            StandardToolParam("todos", "array", True, "List of todo items"),
        ],
        returns="Updated todo list",
        requires_approval=False,
        sandbox_safe=True,
    ),

    # === Notebook Tools ===
    "NotebookEdit": StandardTool(
        name="NotebookEdit",
        category=ToolCategory.NOTEBOOK,
        description="Edit Jupyter notebook cells",
        params=[
            StandardToolParam("notebook_path", "string", True, "Path to notebook"),
            StandardToolParam("new_source", "string", True, "New cell content"),
            StandardToolParam("cell_id", "string", False, "Cell ID to edit"),
            StandardToolParam("edit_mode", "string", False, "replace, insert, or delete"),
        ],
        returns="Updated notebook",
        requires_approval=True,
        sandbox_safe=True,
    ),
}


def get_tool(name: str) -> Optional[StandardTool]:
    """
    Get a standard tool by name or alias.

    Args:
        name: Tool name or alias

    Returns:
        StandardTool if found, None otherwise
    """
    # Direct lookup
    if name in STANDARD_TOOLS:
        return STANDARD_TOOLS[name]

    # Alias lookup
    for tool in STANDARD_TOOLS.values():
        if name in tool.aliases:
            return tool

    return None


def list_tools_by_category(category: ToolCategory) -> List[StandardTool]:
    """
    List all tools in a category.

    Args:
        category: Tool category to filter by

    Returns:
        List of tools in that category
    """
    return [t for t in STANDARD_TOOLS.values() if t.category == category]


def validate_tool_binding(
    tool_name: str,
    params: Optional[Dict[str, Any]] = None,
    custom_tools: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Validate a tool binding against standard or custom tool definitions.

    Args:
        tool_name: Name of the tool to validate
        params: Parameters provided for the tool
        custom_tools: Custom tool definitions from spec

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    params = params or {}

    # Check standard tools first
    tool = get_tool(tool_name)

    # Check custom tools if not found in standard
    if tool is None and custom_tools:
        for custom in custom_tools:
            if custom.get("name") == tool_name:
                # Custom tool found, basic validation only
                return []

    if tool is None:
        errors.append(f"Unknown tool: {tool_name}")
        return errors

    # Validate required parameters
    for param in tool.params:
        if param.required and param.name not in params:
            errors.append(f"Missing required parameter '{param.name}' for tool '{tool_name}'")

    # Validate parameter types (basic check)
    for param_name, param_value in params.items():
        param_def = next((p for p in tool.params if p.name == param_name), None)
        if param_def is None:
            errors.append(f"Unknown parameter '{param_name}' for tool '{tool_name}'")

    return errors


def get_tool_signature(name: str) -> str:
    """
    Get a human-readable signature for a tool.

    Args:
        name: Tool name

    Returns:
        Signature string like "Read(file_path, [offset], [limit])"
    """
    tool = get_tool(name)
    if tool is None:
        return f"{name}(...)"

    required = [p.name for p in tool.params if p.required]
    optional = [f"[{p.name}]" for p in tool.params if not p.required]

    all_params = required + optional
    return f"{name}({', '.join(all_params)})"


def get_allowed_tools_string(tools: List[str]) -> str:
    """
    Format tool list for agentskills.io allowed-tools field.

    Args:
        tools: List of tool names

    Returns:
        Space-delimited string suitable for allowed-tools frontmatter
    """
    return " ".join(tools)
