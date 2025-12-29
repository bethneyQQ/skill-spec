"""
Internationalization (i18n) System for Skill-Spec.

This module provides multi-language support for messages, reports, and templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


# Default locale
DEFAULT_LOCALE = "en"

# Supported locales
SUPPORTED_LOCALES = ["en", "zh"]


@dataclass
class I18nContext:
    """
    Internationalization context for locale management.

    Attributes:
        report_locale: Locale for report messages (en/zh).
        content_locale: Locale for content language detection.
        patterns_locale: Locale for forbidden patterns (en/zh/union).
        template_locale: Locale for SKILL.md templates.
    """

    report_locale: str = DEFAULT_LOCALE
    content_locale: str = DEFAULT_LOCALE
    patterns_locale: str = "union"  # union = both en + zh
    template_locale: str = DEFAULT_LOCALE

    def __post_init__(self):
        """Validate locales."""
        if self.report_locale not in SUPPORTED_LOCALES:
            self.report_locale = DEFAULT_LOCALE
        if self.content_locale not in SUPPORTED_LOCALES:
            self.content_locale = DEFAULT_LOCALE
        if self.patterns_locale not in SUPPORTED_LOCALES + ["union"]:
            self.patterns_locale = "union"
        if self.template_locale not in SUPPORTED_LOCALES:
            self.template_locale = DEFAULT_LOCALE

    @classmethod
    def from_project_yaml(cls, project_yaml_path: Path) -> "I18nContext":
        """Load i18n context from project.yaml."""
        if not project_yaml_path.exists():
            return cls()

        try:
            with open(project_yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError:
            return cls()

        i18n_config = data.get("i18n", {})
        return cls(
            report_locale=i18n_config.get("report_locale", DEFAULT_LOCALE),
            content_locale=i18n_config.get("content_locale", DEFAULT_LOCALE),
            patterns_locale=i18n_config.get("patterns_locale", "union"),
            template_locale=i18n_config.get("template_locale", DEFAULT_LOCALE),
        )


class MessageCatalog:
    """
    Catalog of localized messages.

    Loads messages from YAML files and provides access by key.
    """

    def __init__(self, messages_dir: Optional[Path] = None):
        """
        Initialize the message catalog.

        Args:
            messages_dir: Directory containing message YAML files.
        """
        self.messages_dir = messages_dir
        self._catalogs: Dict[str, Dict[str, Any]] = {}

    def _load_catalog(self, locale: str) -> Dict[str, Any]:
        """Load message catalog for a locale."""
        if locale in self._catalogs:
            return self._catalogs[locale]

        catalog: Dict[str, Any] = {}

        if self.messages_dir:
            messages_file = self.messages_dir / f"{locale}.yaml"
            if messages_file.exists():
                try:
                    with open(messages_file, "r", encoding="utf-8") as f:
                        catalog = yaml.safe_load(f) or {}
                except yaml.YAMLError:
                    pass

        # Fall back to built-in messages
        if not catalog:
            catalog = get_builtin_messages(locale)

        self._catalogs[locale] = catalog
        return catalog

    def get(
        self,
        key: str,
        locale: str = DEFAULT_LOCALE,
        default: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Get a localized message by key.

        Args:
            key: Message key (dot-separated path, e.g., "validation.errors.missing_field").
            locale: Locale to use.
            default: Default value if key not found.
            **kwargs: Format arguments for the message.

        Returns:
            Localized message string.
        """
        catalog = self._load_catalog(locale)

        # Navigate to the key
        parts = key.split(".")
        value: Any = catalog
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                # Try English fallback
                if locale != DEFAULT_LOCALE:
                    return self.get(key, DEFAULT_LOCALE, default, **kwargs)
                return default or key

        if not isinstance(value, str):
            return default or key

        # Format with kwargs
        if kwargs:
            try:
                value = value.format(**kwargs)
            except KeyError:
                pass

        return value

    def get_section(
        self,
        section: str,
        locale: str = DEFAULT_LOCALE,
    ) -> Dict[str, Any]:
        """
        Get all messages in a section.

        Args:
            section: Section key.
            locale: Locale to use.

        Returns:
            Dictionary of messages in the section.
        """
        catalog = self._load_catalog(locale)
        return catalog.get(section, {})


# Global message catalog instance
_message_catalog: Optional[MessageCatalog] = None


def get_message_catalog(messages_dir: Optional[Path] = None) -> MessageCatalog:
    """Get or create the global message catalog."""
    global _message_catalog
    if _message_catalog is None or messages_dir is not None:
        _message_catalog = MessageCatalog(messages_dir)
    return _message_catalog


def t(
    key: str,
    locale: str = DEFAULT_LOCALE,
    default: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Shorthand function to get a localized message.

    Args:
        key: Message key.
        locale: Locale to use.
        default: Default value if key not found.
        **kwargs: Format arguments.

    Returns:
        Localized message string.
    """
    return get_message_catalog().get(key, locale, default, **kwargs)


@lru_cache(maxsize=4)
def get_builtin_messages(locale: str) -> Dict[str, Any]:
    """Get built-in messages for a locale."""
    if locale == "en":
        return ENGLISH_MESSAGES
    elif locale == "zh":
        return CHINESE_MESSAGES
    return ENGLISH_MESSAGES


# Built-in English messages
ENGLISH_MESSAGES: Dict[str, Any] = {
    "validation": {
        "passed": "Validation PASSED",
        "failed": "Validation FAILED",
        "errors": {
            "missing_field": "Missing required field: {field}",
            "invalid_type": "Invalid type for {field}: expected {expected}, got {actual}",
            "unknown_tag": "Unknown tag: {tag}",
            "deprecated_tag": "Tag '{tag}' is deprecated",
            "policy_violation": "Policy violation: {rule}",
        },
        "warnings": {
            "missing_recommended": "Missing recommended field: {field}",
            "low_coverage": "Low coverage score: {score}%",
        },
        "summary": {
            "total_errors": "Total Errors: {count}",
            "total_warnings": "Total Warnings: {count}",
            "structural_coverage": "Structural Coverage: {score}%",
            "behavioral_coverage": "Behavioral Coverage: {score}%",
        },
    },
    "quality": {
        "title": "Quality Analysis",
        "forbidden_pattern": "Forbidden pattern detected: {pattern}",
        "vague_condition": "Vague condition",
        "vague_action": "Vague action",
        "vague_degree": "Vague degree modifier",
        "hedge_word": "Hedge word",
        "weak_verb": "Weak verb",
    },
    "coverage": {
        "title": "Coverage Analysis",
        "gap_found": "Coverage gap: {item}",
        "missing_edge_case": "Missing edge case for: {item}",
        "orphan_definition": "Orphan definition: {item}",
    },
    "compliance": {
        "title": "Compliance Report",
        "policy_checked": "Policies checked: {policies}",
        "violation": "[{severity}] {rule}: {description}",
        "required_action": "Required action: {action}",
    },
    "diary": {
        "title": "Diary Summary",
        "total_events": "Total Events: {count}",
        "test_runs": "Test Runs: {count}",
        "production_runs": "Production Runs: {count}",
        "success_rate": "Success Rate: {rate}%",
        "no_events": "No events recorded",
    },
    "migration": {
        "title": "Migration Guide",
        "success": "Migration completed successfully",
        "items_attention": "Items requiring attention:",
        "next_steps": "Next steps:",
    },
    "cli": {
        "skill_not_found": "Skill '{name}' not found",
        "file_not_found": "File not found: {path}",
        "invalid_format": "Invalid format: {format}",
        "created": "Created: {path}",
        "generated": "Generated: {path}",
        "published": "Published: {name}",
        "archived": "Archived: {name}",
    },
    "sections": {
        "description": "Description",  # Anthropic format (was "purpose")
        "inputs": "Inputs",
        "prerequisites": "Prerequisites",
        "limitations": "Limitations",  # Anthropic format (was "non_goals")
        "decision_criteria": "Decision Criteria",
        "instructions": "Instructions",  # Anthropic format (was "workflow")
        "edge_cases": "Edge Cases",
        "output_format": "Output Format",
        "error_codes": "Error Codes",  # Anthropic format (was "error_handling")
        "when_to_use": "When to Use",  # Anthropic recommended
        "examples": "Examples",  # Anthropic recommended
        "related_skills": "Related Skills",  # Anthropic format (was "works_with")
    },
}


# Built-in Chinese messages
CHINESE_MESSAGES: Dict[str, Any] = {
    "validation": {
        "passed": "验证通过",
        "failed": "验证失败",
        "errors": {
            "missing_field": "缺少必填字段: {field}",
            "invalid_type": "{field} 类型无效: 期望 {expected}, 实际 {actual}",
            "unknown_tag": "未知标签: {tag}",
            "deprecated_tag": "标签 '{tag}' 已弃用",
            "policy_violation": "策略违规: {rule}",
        },
        "warnings": {
            "missing_recommended": "缺少推荐字段: {field}",
            "low_coverage": "覆盖率较低: {score}%",
        },
        "summary": {
            "total_errors": "错误总数: {count}",
            "total_warnings": "警告总数: {count}",
            "structural_coverage": "结构覆盖率: {score}%",
            "behavioral_coverage": "行为覆盖率: {score}%",
        },
    },
    "quality": {
        "title": "质量分析",
        "forbidden_pattern": "检测到禁止模式: {pattern}",
        "vague_condition": "模糊条件",
        "vague_action": "模糊动作",
        "vague_degree": "模糊程度修饰语",
        "hedge_word": "模糊词",
        "weak_verb": "弱动词",
    },
    "coverage": {
        "title": "覆盖率分析",
        "gap_found": "覆盖缺口: {item}",
        "missing_edge_case": "缺少边界案例: {item}",
        "orphan_definition": "孤立定义: {item}",
    },
    "compliance": {
        "title": "合规报告",
        "policy_checked": "已检查策略: {policies}",
        "violation": "[{severity}] {rule}: {description}",
        "required_action": "需要的操作: {action}",
    },
    "diary": {
        "title": "日志摘要",
        "total_events": "总事件数: {count}",
        "test_runs": "测试运行: {count}",
        "production_runs": "生产运行: {count}",
        "success_rate": "成功率: {rate}%",
        "no_events": "无记录事件",
    },
    "migration": {
        "title": "迁移指南",
        "success": "迁移成功完成",
        "items_attention": "需要注意的项目:",
        "next_steps": "下一步:",
    },
    "cli": {
        "skill_not_found": "未找到技能 '{name}'",
        "file_not_found": "文件未找到: {path}",
        "invalid_format": "无效格式: {format}",
        "created": "已创建: {path}",
        "generated": "已生成: {path}",
        "published": "已发布: {name}",
        "archived": "已归档: {name}",
    },
    "sections": {
        "description": "描述",  # Anthropic format (was "purpose")
        "inputs": "输入",
        "prerequisites": "前提条件",
        "limitations": "限制",  # Anthropic format (was "non_goals")
        "decision_criteria": "决策标准",
        "instructions": "操作指南",  # Anthropic format (was "workflow")
        "edge_cases": "边界案例",
        "output_format": "输出格式",
        "error_codes": "错误代码",  # Anthropic format (was "error_handling")
        "when_to_use": "使用场景",  # Anthropic recommended
        "examples": "示例",  # Anthropic recommended
        "related_skills": "相关技能",  # Anthropic format (was "works_with")
    },
}


def create_messages_yaml(locale: str, output_path: Path) -> None:
    """
    Create a messages YAML file for a locale.

    Args:
        locale: Locale to create (en/zh).
        output_path: Path to write the YAML file.
    """
    messages = get_builtin_messages(locale)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(
            messages,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
