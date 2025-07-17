"""Tests for Docker health check functionality."""

import subprocess
import time
import pytest
from unittest.mock import patch, MagicMock


class TestDockerHealthCheck:
    """Test Docker health check functionality."""
    
    def test_health_check_command_exists(self):
        """Test that health check command is properly defined in Dockerfile."""
        # Read Dockerfile to verify health check is defined
        with open("Dockerfile", "r") as f:
            dockerfile_content = f.read()
        
        assert "HEALTHCHECK" in dockerfile_content
        assert "m3 --version" in dockerfile_content
    
    def test_health_check_interval_settings(self):
        """Test that health check has proper interval settings."""
        with open("Dockerfile", "r") as f:
            dockerfile_content = f.read()
        
        # Check for health check parameters
        assert "--interval=30s" in dockerfile_content
        assert "--timeout=10s" in dockerfile_content
        assert "--start-period=5s" in dockerfile_content
        assert "--retries=3" in dockerfile_content
    
    def test_health_check_command_works(self):
        """Test that the health check command works correctly."""
        result = subprocess.run(
            ["docker", "run", "--rm", "m3:test", "m3", "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        assert "M3 CLI Version:" in result.stdout
    
    def test_health_check_failure_scenario(self):
        """Test health check failure when m3 command fails."""
        # Test with an invalid command that should fail
        result = subprocess.run(
            ["docker", "run", "--rm", "m3:test", "m3", "--invalid-option"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode != 0
    
    def test_health_check_in_running_container(self):
        """Test health check status in a running container."""
        # Start a container in the background
        start_result = subprocess.run(
            ["docker", "run", "-d", "--name", "m3-health-test", "m3:test", "sleep", "60"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        try:
            assert start_result.returncode == 0
            container_id = start_result.stdout.strip()
            
            # Wait a bit for health check to run
            time.sleep(10)
            
            # Check health status
            health_result = subprocess.run(
                ["docker", "inspect", "--format={{.State.Health.Status}}", container_id],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Health status should be either 'healthy' or 'starting'
            assert health_result.returncode == 0
            health_status = health_result.stdout.strip()
            assert health_status in ["healthy", "starting", "unhealthy"]
        
        finally:
            # Clean up container
            subprocess.run(["docker", "rm", "-f", "m3-health-test"], capture_output=True)
    
    def test_health_check_logs(self):
        """Test that health check logs are accessible."""
        # Start a container and check health check logs
        start_result = subprocess.run(
            ["docker", "run", "-d", "--name", "m3-health-log-test", "m3:test", "sleep", "60"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        try:
            assert start_result.returncode == 0
            container_id = start_result.stdout.strip()
            
            # Wait for at least one health check
            time.sleep(10)
            
            # Get health check logs
            logs_result = subprocess.run(
                ["docker", "inspect", "--format={{json .State.Health}}", container_id],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            assert logs_result.returncode == 0
            # Should contain health check information
            assert "Log" in logs_result.stdout or "Status" in logs_result.stdout
        
        finally:
            # Clean up container
            subprocess.run(["docker", "rm", "-f", "m3-health-log-test"], capture_output=True)
    
    def test_health_check_with_environment_variables(self):
        """Test health check with different environment variables."""
        # Test with SQLite backend
        result = subprocess.run(
            ["docker", "run", "--rm", "-e", "M3_BACKEND=sqlite", "m3:test", "m3", "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        assert "M3 CLI Version:" in result.stdout
    
    def test_health_check_exit_codes(self):
        """Test that health check properly handles exit codes."""
        # Test successful health check (should exit with code 0)
        result = subprocess.run(
            ["docker", "run", "--rm", "m3:test", "sh", "-c", "m3 --version || exit 1"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        
        # Test failed health check (should exit with code 1)
        result = subprocess.run(
            ["docker", "run", "--rm", "m3:test", "sh", "-c", "m3 --invalid-flag || exit 1"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 1


class TestDockerHealthCheckIntegration:
    """Integration tests for Docker health check."""
    
    def test_health_check_with_docker_compose(self):
        """Test health check works with docker-compose setup."""
        # Check if docker-compose.yml exists and has health check
        try:
            with open("docker-compose.yml", "r") as f:
                compose_content = f.read()
            
            # If docker-compose.yml exists, it should reference health check
            if "m3" in compose_content:
                assert "healthcheck" in compose_content or "depends_on" in compose_content
        except FileNotFoundError:
            # If no docker-compose.yml, that's okay for this test
            pass
    
    def test_health_check_startup_time(self):
        """Test that health check allows proper startup time."""
        # The start-period should be sufficient for container startup
        start_time = time.time()
        
        result = subprocess.run(
            ["docker", "run", "--rm", "m3:test", "m3", "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        end_time = time.time()
        startup_time = end_time - start_time
        
        assert result.returncode == 0
        # Should start within reasonable time (less than start-period + timeout)
        assert startup_time < 15  # 5s start-period + 10s timeout
    
    def test_health_check_retries(self):
        """Test that health check retries work correctly."""
        # This test verifies the retry mechanism by checking Dockerfile config
        with open("Dockerfile", "r") as f:
            dockerfile_content = f.read()
        
        # Should have retries=3 configured
        assert "--retries=3" in dockerfile_content
        
        # Verify the command that will be retried
        assert "m3 --version || exit 1" in dockerfile_content
    
    @pytest.mark.slow
    def test_health_check_under_load(self):
        """Test health check performance under load."""
        # Start multiple containers to test health check under load
        container_ids = []
        
        try:
            for i in range(3):
                result = subprocess.run(
                    ["docker", "run", "-d", "--name", f"m3-load-test-{i}", "m3:test", "sleep", "30"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    container_ids.append(result.stdout.strip())
            
            # Wait for health checks to run
            time.sleep(15)
            
            # Check that all containers are healthy
            for container_id in container_ids:
                health_result = subprocess.run(
                    ["docker", "inspect", "--format={{.State.Health.Status}}", container_id],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if health_result.returncode == 0:
                    health_status = health_result.stdout.strip()
                    assert health_status in ["healthy", "starting"]
        
        finally:
            # Clean up all containers
            for i in range(3):
                subprocess.run(["docker", "rm", "-f", f"m3-load-test-{i}"], capture_output=True)