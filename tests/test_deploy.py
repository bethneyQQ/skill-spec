"""
Tests for Deployment Module.
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from backend.skillspec.deploy import (
    DeploymentTarget,
    DeploymentBundle,
    PreflightCheck,
    PreflightResult,
    TargetRegistry,
    BundleCreator,
    PreflightChecker,
    create_deployment_bundle,
    run_preflight_checks,
)


class TestDeploymentTarget:
    """Tests for DeploymentTarget dataclass."""

    def test_from_dict(self):
        """Test creating target from dictionary."""
        data = {
            "name": "production",
            "url": "https://api.example.com/skills",
            "auth_type": "api_key",
            "env_var": "PROD_API_KEY",
            "description": "Production environment",
        }
        target = DeploymentTarget.from_dict(data)
        assert target.name == "production"
        assert target.url == "https://api.example.com/skills"
        assert target.auth_type == "api_key"
        assert target.env_var == "PROD_API_KEY"

    def test_to_dict(self):
        """Test converting target to dictionary."""
        target = DeploymentTarget(
            name="staging",
            url="https://staging.example.com",
            auth_type="none",
        )
        data = target.to_dict()
        assert data["name"] == "staging"
        assert data["url"] == "https://staging.example.com"

    def test_default_auth_type(self):
        """Test default auth type is 'none'."""
        target = DeploymentTarget(name="local", url="http://localhost:8080")
        assert target.auth_type == "none"


class TestDeploymentBundle:
    """Tests for DeploymentBundle dataclass."""

    def test_to_dict(self):
        """Test converting bundle to dictionary."""
        bundle = DeploymentBundle(
            skill_name="test-skill",
            version="1.0.0",
            created_at="2024-01-15T10:00:00Z",
            files=["spec.yaml", "SKILL.md"],
            checksum="abc123",
        )
        data = bundle.to_dict()
        assert data["skill_name"] == "test-skill"
        assert data["version"] == "1.0.0"
        assert len(data["files"]) == 2


class TestPreflightCheck:
    """Tests for PreflightCheck dataclass."""

    def test_passed_check(self):
        """Test creating passed check."""
        check = PreflightCheck(
            name="spec_exists",
            passed=True,
            message="spec.yaml found",
        )
        assert check.passed is True

    def test_failed_check(self):
        """Test creating failed check."""
        check = PreflightCheck(
            name="validation",
            passed=False,
            message="Validation failed: 3 errors",
            severity="error",
        )
        assert check.passed is False
        assert check.severity == "error"

    def test_to_dict(self):
        """Test converting check to dictionary."""
        check = PreflightCheck(
            name="test",
            passed=True,
            message="OK",
        )
        data = check.to_dict()
        assert "name" in data
        assert "passed" in data
        assert "message" in data


class TestPreflightResult:
    """Tests for PreflightResult dataclass."""

    def test_overall_success(self):
        """Test overall success calculation."""
        result = PreflightResult(
            success=True,
            checks=[
                PreflightCheck(name="c1", passed=True, message="OK"),
                PreflightCheck(name="c2", passed=True, message="OK"),
            ],
        )
        assert result.success is True

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = PreflightResult(
            success=True,
            checks=[PreflightCheck(name="test", passed=True, message="OK")],
            target="production",
        )
        data = result.to_dict()
        assert data["success"] is True
        assert data["target"] == "production"
        assert len(data["checks"]) == 1


class TestTargetRegistry:
    """Tests for TargetRegistry class."""

    def test_add_and_get_target(self):
        """Test adding and retrieving target."""
        with tempfile.TemporaryDirectory() as tmpdir:
            targets_path = Path(tmpdir) / "targets.yaml"
            registry = TargetRegistry(targets_path)

            target = DeploymentTarget(
                name="test",
                url="http://test.com",
            )
            registry.add_target(target)

            retrieved = registry.get_target("test")
            assert retrieved is not None
            assert retrieved.url == "http://test.com"

    def test_remove_target(self):
        """Test removing target."""
        with tempfile.TemporaryDirectory() as tmpdir:
            targets_path = Path(tmpdir) / "targets.yaml"
            registry = TargetRegistry(targets_path)

            target = DeploymentTarget(name="remove_me", url="http://x.com")
            registry.add_target(target)
            assert registry.get_target("remove_me") is not None

            removed = registry.remove_target("remove_me")
            assert removed is True
            assert registry.get_target("remove_me") is None

    def test_remove_nonexistent_target(self):
        """Test removing non-existent target."""
        with tempfile.TemporaryDirectory() as tmpdir:
            targets_path = Path(tmpdir) / "targets.yaml"
            registry = TargetRegistry(targets_path)

            removed = registry.remove_target("nonexistent")
            assert removed is False

    def test_list_targets(self):
        """Test listing all targets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            targets_path = Path(tmpdir) / "targets.yaml"
            registry = TargetRegistry(targets_path)

            registry.add_target(DeploymentTarget(name="t1", url="http://1.com"))
            registry.add_target(DeploymentTarget(name="t2", url="http://2.com"))

            targets = registry.list_targets()
            assert len(targets) == 2

    def test_persistence(self):
        """Test that targets persist to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            targets_path = Path(tmpdir) / "targets.yaml"

            # Create and add target
            registry1 = TargetRegistry(targets_path)
            registry1.add_target(DeploymentTarget(name="persist", url="http://p.com"))

            # Create new registry from same file
            registry2 = TargetRegistry(targets_path)
            target = registry2.get_target("persist")
            assert target is not None
            assert target.url == "http://p.com"


class TestBundleCreator:
    """Tests for BundleCreator class."""

    def test_create_bundle(self):
        """Test creating deployment bundle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()

            # Create minimal skill files
            spec_content = {
                "skill": {
                    "name": "test-skill",
                    "version": "1.0.0",
                }
            }
            (skill_dir / "spec.yaml").write_text(
                yaml.dump(spec_content), encoding="utf-8"
            )
            (skill_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

            # Create bundle
            output_path = Path(tmpdir) / "output" / "test.zip"
            creator = BundleCreator(skill_dir)
            bundle = creator.create_bundle(output_path)

            assert output_path.exists()
            assert bundle.skill_name == "test-skill"
            assert bundle.version == "1.0.0"
            assert len(bundle.checksum) > 0
            # Note: spec.yaml is intentionally excluded from runtime bundles
            # Only SKILL.md and resources are included
            assert "SKILL.md" in bundle.files
            assert "spec.yaml" not in bundle.files

    def test_create_bundle_with_optional_files(self):
        """Test creating bundle with optional files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()

            # Create files
            spec_content = {"skill": {"name": "test-skill", "version": "1.0.0"}}
            (skill_dir / "spec.yaml").write_text(
                yaml.dump(spec_content), encoding="utf-8"
            )
            (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")
            (skill_dir / "README.md").write_text("# README", encoding="utf-8")

            # Create optional directories
            (skill_dir / "examples").mkdir()
            (skill_dir / "examples" / "example.yaml").write_text(
                "example: true", encoding="utf-8"
            )

            output_path = Path(tmpdir) / "output" / "test.zip"
            creator = BundleCreator(skill_dir)
            bundle = creator.create_bundle(output_path, include_optional=True)

            assert "README.md" in bundle.files
            assert any("examples" in f for f in bundle.files)

    def test_create_bundle_missing_spec(self):
        """Test that missing spec.yaml raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "empty-skill"
            skill_dir.mkdir()

            output_path = Path(tmpdir) / "output.zip"
            creator = BundleCreator(skill_dir)

            with pytest.raises(FileNotFoundError):
                creator.create_bundle(output_path)

    def test_manifest_creation(self):
        """Test that manifest file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()

            spec_content = {"skill": {"name": "test", "version": "1.0.0"}}
            (skill_dir / "spec.yaml").write_text(
                yaml.dump(spec_content), encoding="utf-8"
            )

            output_path = Path(tmpdir) / "output" / "bundle.zip"
            creator = BundleCreator(skill_dir)
            creator.create_bundle(output_path)

            manifest_path = output_path.with_suffix(".manifest.json")
            assert manifest_path.exists()


class TestPreflightChecker:
    """Tests for PreflightChecker class."""

    def test_spec_exists_check_passes(self):
        """Test spec_exists check when spec.yaml exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            (skill_dir / "spec.yaml").write_text("skill: {}", encoding="utf-8")

            checker = PreflightChecker(skill_dir)
            check = checker._check_spec_exists()
            assert check.passed is True

    def test_spec_exists_check_fails(self):
        """Test spec_exists check when spec.yaml missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)

            checker = PreflightChecker(skill_dir)
            check = checker._check_spec_exists()
            assert check.passed is False

    def test_skill_md_exists_check(self):
        """Test skill_md_exists check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

            checker = PreflightChecker(skill_dir)
            check = checker._check_skill_md_exists()
            assert check.passed is True

    def test_version_check_passes(self):
        """Test version check with valid version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            spec_content = {"skill": {"version": "1.0.0"}}
            (skill_dir / "spec.yaml").write_text(
                yaml.dump(spec_content), encoding="utf-8"
            )

            checker = PreflightChecker(skill_dir)
            check = checker._check_version()
            assert check.passed is True
            assert "1.0.0" in check.message

    def test_version_check_fails_todo(self):
        """Test version check fails when version is TODO."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            spec_content = {"skill": {"version": "TODO"}}
            (skill_dir / "spec.yaml").write_text(
                yaml.dump(spec_content), encoding="utf-8"
            )

            checker = PreflightChecker(skill_dir)
            check = checker._check_version()
            assert check.passed is False

    def test_no_todos_check_passes(self):
        """Test TODO check when no TODOs present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            (skill_dir / "spec.yaml").write_text(
                "skill:\n  name: clean\n  version: 1.0.0", encoding="utf-8"
            )

            checker = PreflightChecker(skill_dir)
            check = checker._check_no_todos()
            assert check.passed is True

    def test_no_todos_check_fails(self):
        """Test TODO check when TODOs present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            (skill_dir / "spec.yaml").write_text(
                "skill:\n  name: TODO\n  purpose: TODO", encoding="utf-8"
            )

            checker = PreflightChecker(skill_dir)
            check = checker._check_no_todos()
            assert check.passed is False
            assert "2" in check.message  # 2 TODOs

    def test_target_auth_check_no_auth(self):
        """Test auth check with no authentication."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            target = DeploymentTarget(
                name="local",
                url="http://localhost",
                auth_type="none",
            )

            checker = PreflightChecker(skill_dir)
            check = checker._check_target_auth(target)
            assert check.passed is True

    def test_target_auth_check_missing_env(self):
        """Test auth check with missing env var."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            target = DeploymentTarget(
                name="prod",
                url="http://prod.com",
                auth_type="api_key",
                env_var="NONEXISTENT_API_KEY_12345",
            )

            checker = PreflightChecker(skill_dir)
            check = checker._check_target_auth(target)
            assert check.passed is False
            assert "NONEXISTENT_API_KEY_12345" in check.message

    def test_run_all_checks(self):
        """Test running all preflight checks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            spec_content = {"skill": {"name": "test", "version": "1.0.0"}}
            (skill_dir / "spec.yaml").write_text(
                yaml.dump(spec_content), encoding="utf-8"
            )
            (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

            checker = PreflightChecker(skill_dir)
            result = checker.run_checks()

            assert result.success is True
            assert len(result.checks) >= 4  # At least 4 basic checks


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_deployment_bundle(self):
        """Test create_deployment_bundle function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "skill"
            skill_dir.mkdir()
            output_dir = Path(tmpdir) / "output"

            spec_content = {"skill": {"name": "func-test", "version": "2.0.0"}}
            (skill_dir / "spec.yaml").write_text(
                yaml.dump(spec_content), encoding="utf-8"
            )

            bundle = create_deployment_bundle(skill_dir, output_dir)
            assert bundle.skill_name == "func-test"
            assert bundle.version == "2.0.0"

    def test_run_preflight_checks(self):
        """Test run_preflight_checks function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            spec_content = {"skill": {"name": "preflight", "version": "1.0.0"}}
            (skill_dir / "spec.yaml").write_text(
                yaml.dump(spec_content), encoding="utf-8"
            )
            (skill_dir / "SKILL.md").write_text("# Preflight", encoding="utf-8")

            result = run_preflight_checks(skill_dir)
            assert result.success is True
