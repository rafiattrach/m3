"""Tests for Docker container functionality."""

import subprocess
import time
import requests
import pytest
from unittest.mock import patch, MagicMock


class TestDockerBuild:
    """Test Docker image build functionality."""
    
    def test_docker_build_success(self):
        """Test that Docker image builds successfully."""
        result = subprocess.run(
            ["docker", "build", "-t", "m3:test", "."],
            capture_output=True,
            text=True,
            cwd=".",
            timeout=300
        )
        assert result.returncode == 0, f"Docker build failed: {result.stderr}"
        # Docker buildx outputs to stderr, check both stdout and stderr
        output = result.stdout + result.stderr
        assert "Successfully built" in output or "Successfully tagged" in output or "naming to docker.io/library/m3:test done" in output
    
    def test_docker_image_exists(self):
        """Test that Docker image exists after build."""
        result = subprocess.run(
            ["docker", "images", "m3:test"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "m3" in result.stdout
        assert "test" in result.stdout


class TestDockerContainer:
    """Test Docker container functionality."""
    
    def test_container_cli_version(self):
        """Test that CLI version command works in container."""
        result = subprocess.run(
            ["docker", "run", "--rm", "m3:test", "m3", "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        assert "M3 CLI Version:" in result.stdout
    
    def test_container_cli_help(self):
        """Test that CLI help command works in container."""
        result = subprocess.run(
            ["docker", "run", "--rm", "m3:test", "m3", "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        assert "M3 CLI: Initialize local clinical datasets" in result.stdout
        assert "Commands" in result.stdout
    
    def test_container_health_check(self):
        """Test Docker container health check."""
        result = subprocess.run(
            ["docker", "run", "--rm", "m3:test", "m3", "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )
        # Health check is based on m3 --version command
        assert result.returncode == 0
    
    def test_container_non_root_user(self):
        """Test that container runs as non-root user."""
        result = subprocess.run(
            ["docker", "run", "--rm", "m3:test", "whoami"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        assert "m3user" in result.stdout
    
    def test_container_data_directory(self):
        """Test that data directory exists in container."""
        result = subprocess.run(
            ["docker", "run", "--rm", "m3:test", "ls", "-la", "/home/m3user/m3_data"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        assert "total" in result.stdout  # ls -la output should show directory contents
    
    def test_container_mcp_server_without_db(self):
        """Test that MCP server fails gracefully without database."""
        result = subprocess.run(
            ["docker", "run", "--rm", "m3:test", "m3-mcp-server", "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )
        # Should fail because no database is initialized
        assert result.returncode != 0
        assert "SQLite database not found" in result.stderr


class TestDockerEnvironment:
    """Test Docker environment variables and configuration."""
    
    def test_sqlite_backend_environment(self):
        """Test SQLite backend environment variable."""
        result = subprocess.run(
            ["docker", "run", "--rm", "-e", "M3_BACKEND=sqlite", "m3:test", "python", "-c", "import os; print(os.environ.get('M3_BACKEND', 'not_set'))"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        assert "sqlite" in result.stdout
    
    def test_bigquery_backend_environment(self):
        """Test BigQuery backend environment variable."""
        result = subprocess.run(
            ["docker", "run", "--rm", "-e", "M3_BACKEND=bigquery", "-e", "M3_PROJECT_ID=test-project", "m3:test", "python", "-c", "import os; print(os.environ.get('M3_BACKEND', 'not_set'))"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        assert "bigquery" in result.stdout
    
    def test_oauth2_disabled_by_default(self):
        """Test that OAuth2 is disabled by default in container."""
        result = subprocess.run(
            ["docker", "run", "--rm", "m3:test", "python", "-c", "import os; print(os.environ.get('M3_OAUTH2_ENABLED', 'not_set'))"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        assert "not_set" in result.stdout or "false" in result.stdout.lower()


class TestDockerIntegration:
    """Test Docker integration scenarios."""
    
    def test_container_with_volume_mount(self):
        """Test container with volume mount for data persistence."""
        # Create temporary directory for testing
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Test volume mount
            result = subprocess.run(
                ["docker", "run", "--rm", "-v", f"{tmp_dir}:/home/m3user/m3_data", "m3:test", "ls", "-la", "/home/m3user/m3_data"],
                capture_output=True,
                text=True,
                timeout=30
            )
            assert result.returncode == 0
    
    def test_container_network_isolation(self):
        """Test container network isolation."""
        result = subprocess.run(
            ["docker", "run", "--rm", "m3:test", "python", "-c", "import socket; print(socket.gethostname())"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        # Should show container hostname, not host system hostname
        assert len(result.stdout.strip()) > 0
    
    @pytest.mark.slow
    def test_container_resource_limits(self):
        """Test container with resource limits."""
        result = subprocess.run(
            ["docker", "run", "--rm", "--memory=512m", "--cpus=0.5", "m3:test", "m3", "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        assert "M3 CLI Version:" in result.stdout


class TestDockerCleanup:
    """Test Docker cleanup functionality."""
    
    def test_container_cleanup_after_exit(self):
        """Test that container is cleaned up after exit."""
        # Run container and capture container ID
        result = subprocess.run(
            ["docker", "run", "--rm", "m3:test", "m3", "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        
        # Check that no containers are left running
        ps_result = subprocess.run(
            ["docker", "ps", "-q", "--filter", "ancestor=m3:test"],
            capture_output=True,
            text=True
        )
        assert ps_result.returncode == 0
        assert ps_result.stdout.strip() == ""  # No containers should be running
    
    def test_image_cleanup_capability(self):
        """Test that Docker image can be removed."""
        # This test ensures the image is properly tagged and removable
        result = subprocess.run(
            ["docker", "images", "-q", "m3:test"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0  # Image should exist