#!/usr/bin/env python3
"""
MIMIC-IV Demo Evaluation Script
Evaluates MIMIC-IV questions from EHRSQL 2024 dataset using Goose with M3 MCP server.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from dataset.download import EHRSQLDatasetDownloader
from evaluators.goose_evaluator import GooseMCPEvaluator
from rich.console import Console


def setup_results_directory() -> Path:
    """Setup results directory for this evaluation run."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(__file__).parent / "results" / f"mimic_iv_demo_goose_{timestamp}"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def save_results(results: list[dict], summary: dict, results_dir: Path):
    """Save evaluation results to files."""
    # Save detailed results
    with open(results_dir / "detailed_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Save summary
    with open(results_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Save questions and SQL for easy review
    questions_and_sql = []
    for result in results:
        questions_and_sql.append(
            {
                "question": result["question"],
                "final_answer": result.get("final_answer", ""),
                "tools_used": result.get("tools_used", []),
                "natural_tool_discovery": result.get("natural_tool_discovery", False),
                "successful": result.get("mcp_session_successful", False),
            }
        )

    with open(results_dir / "questions_and_sql.json", "w") as f:
        json.dump(questions_and_sql, f, indent=2)

    # Save full conversation logs to separate files
    logs_dir = results_dir / "conversation_logs"
    logs_dir.mkdir(exist_ok=True)

    for i, result in enumerate(results):
        if result.get("conversation_log"):
            log_filename = f"question_{i + 1}_conversation.txt"
            with open(logs_dir / log_filename, "w") as f:
                f.write(f"Question: {result['question']}\n")
                f.write("=" * 80 + "\n\n")
                f.write("FULL GOOSE CONVERSATION LOG:\n")
                f.write("-" * 40 + "\n")
                f.write(result["conversation_log"])
                f.write("\n" + "-" * 40 + "\n")
                f.write(f"\nGenerated SQL: {result.get('final_answer', 'None')}\n")
                f.write(f"Success: {result.get('mcp_session_successful', False)}\n")
                f.write(f"Error: {result.get('error', 'None')}\n")
                f.write(f"Tools Used: {result.get('tools_used', [])}\n")


def main():
    """Main evaluation function."""
    parser = argparse.ArgumentParser(
        description="Evaluate MIMIC-IV demo questions using Goose with M3 MCP"
    )
    parser.add_argument(
        "--max-questions",
        type=int,
        default=10,
        help="Maximum number of questions to evaluate (default: 10)",
    )
    parser.add_argument(
        "--split",
        choices=["train", "valid", "test"],
        default="valid",
        help="Dataset split to use (default: valid)",
    )
    parser.add_argument(
        "--model",
        default="qwen3:4b",
        help="Model to use with Goose (default: qwen3:4b)",
    )

    args = parser.parse_args()

    console = Console()
    console.print(
        "[bold blue]🦆 MIMIC-IV Demo Evaluation with Goose + M3 MCP[/bold blue]"
    )

    # Setup
    console.print("\n[cyan]📁 Setting up evaluation...[/cyan]")
    results_dir = setup_results_directory()
    console.print(f"Results will be saved to: {results_dir}")

    # Load dataset
    console.print("\n[cyan]📊 Loading EHRSQL 2024 dataset...[/cyan]")
    downloader = EHRSQLDatasetDownloader()

    try:
        # Load MIMIC-IV questions from EHRSQL 2024
        all_questions = downloader.get_answerable_questions(args.split)
        console.print(
            f"Loaded {len(all_questions)} answerable questions from MIMIC-IV {args.split} split"
        )
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print(
            "[yellow]Please download the dataset first by running the download script[/yellow]"
        )
        return 1

    # Limit questions if requested
    if args.max_questions and len(all_questions) > args.max_questions:
        all_questions = all_questions[: args.max_questions]
        console.print(
            f"[yellow]Limited to {args.max_questions} questions for testing[/yellow]"
        )

    if not all_questions:
        console.print("[red]No questions found![/red]")
        return 1

    # Extract just the question text for evaluation
    question_texts = [q["question"] for q in all_questions]

    # Run evaluation with Goose
    console.print(f"\n[cyan]🦆 Starting Goose evaluation with {args.model}...[/cyan]")
    try:
        evaluator = GooseMCPEvaluator(model=args.model)
        results = evaluator.evaluate_questions(question_texts)
        summary = evaluator.get_summary_report()
    except Exception as e:
        console.print(f"[red]Error during evaluation: {e}[/red]")
        return 1

    # Add original question metadata back to results
    for i, result in enumerate(results):
        if i < len(all_questions):
            original_q = all_questions[i]
            result.update(
                {
                    "original_id": original_q.get("id"),
                    "expected_sql": original_q.get("expected_sql"),
                    "db_id": original_q.get("db_id"),
                    "is_impossible": original_q.get("is_impossible", False),
                }
            )

    # Save results
    console.print("\n[cyan]💾 Saving results...[/cyan]")
    save_results(results, summary, results_dir)

    # Print summary
    console.print("\n[bold green]📊 Evaluation Summary[/bold green]")
    console.print(f"Total questions evaluated: {summary['total_questions']}")
    console.print(f"Successful MCP sessions: {summary['successful_mcp_sessions']}")
    console.print(
        f"MCP session success rate: {summary['mcp_session_success_rate']:.2%}"
    )
    console.print(
        f"Natural tool discovery rate: {summary['natural_tool_discovery_rate']:.2%}"
    )
    console.print(f"Questions with tool usage: {summary['questions_with_tool_usage']}")
    console.print(f"Model used: {summary['model']}")

    if summary.get("tool_usage_frequency"):
        console.print("\n[bold blue]🔧 Tool Usage:[/bold blue]")
        for tool, count in summary["tool_usage_frequency"].items():
            console.print(f"  {tool}: {count} times")

    console.print(f"\n[green]✅ Results saved to: {results_dir}[/green]")

    return 0


if __name__ == "__main__":
    exit(main())
