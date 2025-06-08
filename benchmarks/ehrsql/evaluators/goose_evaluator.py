"""
Goose MCP Tools Evaluator for MIMIC-IV Questions
Tests M3 MCP tools performance by sending raw questions and measuring natural tool discovery.
"""

import os
import subprocess
import time
import uuid
from pathlib import Path

from rich.console import Console


class GooseMCPEvaluator:
    """Evaluator that tests natural MCP tool discovery by sending raw questions to Goose."""

    def __init__(self, model: str = "qwen3:4b", **kwargs):
        self.model = model
        self.console = Console()
        self.results = []

        # Verify Goose is available and configured with M3 MCP
        if not self._check_goose_available():
            raise RuntimeError("Goose CLI not found. Please install Goose first.")

        if not self._check_mcp_configured():
            raise RuntimeError(
                "M3 MCP server not configured in Goose. Please run setup script first."
            )

    def _check_goose_available(self) -> bool:
        """Check if Goose CLI is available."""
        try:
            env = os.environ.copy()
            env["PATH"] = f"{Path.home()}/.local/bin:" + env.get("PATH", "")

            result = subprocess.run(
                ["goose", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _check_mcp_configured(self) -> bool:
        """Check if M3 MCP server is configured in Goose."""
        try:
            goose_config_path = Path.home() / ".config" / "goose" / "config.yaml"
            if not goose_config_path.exists():
                return False

            with open(goose_config_path) as f:
                config_content = f.read()
                # Check for M3 MCP server configuration
                return (
                    "m3-mimic-demo" in config_content and "M3_DB_PATH" in config_content
                )
        except Exception:
            return False

    def _run_goose_mcp_session(self, question: str) -> dict:
        """Run a Goose session with raw question to test natural MCP tool discovery."""
        session_log = {
            "question": question,
            "conversation": "",
            "tools_used": [],
            "successful_tool_calls": 0,
            "failed_tool_calls": 0,
            "final_answer": "",
            "execution_successful": False,
            "error": None,
        }

        try:
            # Send ONLY the raw question - no prompting about tools!
            # This tests if the LLM naturally discovers and uses MCP tools
            prompt = question

            # Set up environment
            env = os.environ.copy()
            env["PATH"] = f"{Path.home()}/.local/bin:" + env.get("PATH", "")

            # Use unique session name to avoid conflicts
            session_name = f"mcp-eval-{uuid.uuid4().hex[:8]}"

            # Run Goose session with MCP tools enabled
            self.console.print(f"[dim]Starting Goose session: {session_name}[/dim]")

            # Build Goose command with provider
            goose_cmd = ["goose", "session", "--name", session_name]

            result = subprocess.run(
                goose_cmd,
                input=prompt + "\n\nexit\n",  # Add exit to end session cleanly
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                env=env,
            )

            session_log["conversation"] = result.stdout
            session_log["execution_successful"] = result.returncode == 0

            if result.stderr:
                session_log["error"] = result.stderr

            # Parse the conversation for MCP tool usage
            self._parse_mcp_tool_usage(result.stdout, session_log)

            # Extract final answer
            session_log["final_answer"] = self._extract_final_answer(result.stdout)

        except subprocess.TimeoutExpired:
            session_log["error"] = "Goose MCP session timed out"
            session_log["execution_successful"] = False
        except Exception as e:
            session_log["error"] = str(e)
            session_log["execution_successful"] = False

        return session_log

    def _parse_mcp_tool_usage(self, conversation: str, session_log: dict):
        """Parse conversation to extract MCP tool usage statistics."""
        lines = conversation.split("\n")
        tools_used = []
        successful_calls = 0
        failed_calls = 0

        for line in lines:
            line_lower = line.lower()

            # Look for tool usage indicators
            if any(
                indicator in line_lower
                for indicator in [
                    "tool:",
                    "function:",
                    "calling",
                    "using tool",
                    "tool call",
                    "execute",
                    "query",
                    "schema",
                    "m3_",
                    "database",
                ]
            ):
                # Extract tool name
                for word in line.split():
                    if word.startswith(("m3_", "query_", "schema_", "database_")):
                        if word not in tools_used:
                            tools_used.append(word)

            # Count successful/failed tool calls
            if any(
                success_indicator in line_lower
                for success_indicator in ["success", "result:", "returned", "completed"]
            ):
                successful_calls += 1
            elif any(
                error_indicator in line_lower
                for error_indicator in ["error", "failed", "exception", "timeout"]
            ):
                failed_calls += 1

        session_log["tools_used"] = tools_used
        session_log["successful_tool_calls"] = successful_calls
        session_log["failed_tool_calls"] = failed_calls

    def _extract_final_answer(self, conversation: str) -> str:
        """Extract the final answer from the conversation."""
        lines = conversation.split("\n")

        # Look for final answer patterns
        answer_lines = []
        capture_answer = False

        for line in lines:
            line_lower = line.lower()

            # Start capturing after answer indicators
            if any(
                indicator in line_lower
                for indicator in [
                    "final answer:",
                    "answer:",
                    "conclusion:",
                    "result:",
                    "the answer is",
                    "therefore",
                    "in summary",
                ]
            ):
                capture_answer = True
                answer_lines.append(line)
            elif capture_answer and line.strip():
                answer_lines.append(line)
            elif capture_answer and not line.strip():
                # Stop at empty line after answer
                break

        return "\n".join(answer_lines).strip() if answer_lines else ""

    def evaluate_question(self, question: str) -> dict:
        """Evaluate a single question using Goose with natural MCP tool discovery."""
        self.console.print(
            f"[cyan]🔧 Testing natural MCP tool discovery: {question[:80]}...[/cyan]"
        )

        session_result = self._run_goose_mcp_session(question)

        # Calculate MCP effectiveness metrics
        total_tool_calls = (
            session_result["successful_tool_calls"]
            + session_result["failed_tool_calls"]
        )
        tool_success_rate = session_result["successful_tool_calls"] / max(
            total_tool_calls, 1
        )

        result = {
            "question": question,
            "final_answer": session_result["final_answer"],
            "tools_used": session_result["tools_used"],
            "successful_tool_calls": session_result["successful_tool_calls"],
            "failed_tool_calls": session_result["failed_tool_calls"],
            "tool_success_rate": tool_success_rate,
            "natural_tool_discovery": len(session_result["tools_used"]) > 0,
            "mcp_session_successful": session_result["execution_successful"],
            "error": session_result.get("error"),
            "conversation_log": session_result["conversation"],
            "evaluator": "goose-mcp-natural",
        }

        # Display results
        if result["mcp_session_successful"]:
            self.console.print("[green]✅ Session completed[/green]")
            if result["natural_tool_discovery"]:
                self.console.print(
                    f"[green]🔧 Discovered {len(result['tools_used'])} tools naturally[/green]"
                )
            else:
                self.console.print("[yellow]⚠️  No tools discovered/used[/yellow]")
        else:
            self.console.print(f"[red]❌ Session failed: {result['error']}[/red]")

        self.results.append(result)
        return result

    def evaluate_questions(self, questions: list[str]) -> list[dict]:
        """Evaluate multiple questions using natural MCP tool discovery."""
        self.console.print(
            f"[yellow]🔧 Testing natural MCP tool discovery on {len(questions)} questions[/yellow]"
        )

        results = []
        for i, question in enumerate(questions, 1):
            self.console.print(f"\n[blue]Question {i}/{len(questions)}[/blue]")
            result = self.evaluate_question(question)
            results.append(result)

            # Brief pause between questions to avoid overwhelming the system
            time.sleep(1)

        return results

    def get_summary_report(self) -> dict:
        """Generate summary report focused on natural MCP tool discovery."""
        if not self.results:
            return {"error": "No results to summarize"}

        total_questions = len(self.results)
        successful_sessions = sum(
            1 for r in self.results if r["mcp_session_successful"]
        )
        natural_discovery = sum(1 for r in self.results if r["natural_tool_discovery"])

        # Tool usage statistics
        all_tools = []
        total_successful_calls = sum(r["successful_tool_calls"] for r in self.results)
        total_failed_calls = sum(r["failed_tool_calls"] for r in self.results)

        for result in self.results:
            all_tools.extend(result["tools_used"])

        # Count tool usage frequency
        tool_usage = {}
        for tool in all_tools:
            tool_usage[tool] = tool_usage.get(tool, 0) + 1

        return {
            "total_questions": total_questions,
            "successful_mcp_sessions": successful_sessions,
            "mcp_session_success_rate": successful_sessions / total_questions,
            "natural_tool_discovery_rate": natural_discovery / total_questions,
            "questions_with_tool_usage": natural_discovery,
            "total_tool_calls": total_successful_calls + total_failed_calls,
            "successful_tool_calls": total_successful_calls,
            "failed_tool_calls": total_failed_calls,
            "overall_tool_success_rate": total_successful_calls
            / max(total_successful_calls + total_failed_calls, 1),
            "unique_tools_used": len(set(all_tools)),
            "tool_usage_frequency": tool_usage,
            "avg_tools_per_question": len(all_tools) / total_questions,
            "model": self.model,
            "evaluator": "goose-mcp-natural",
        }
