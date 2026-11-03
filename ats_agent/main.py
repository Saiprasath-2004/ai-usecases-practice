"""Command-line entry point for running ATS evaluations."""

import argparse
from pathlib import Path

from ats_agent.graph.builder import build_graph
from ats_agent.batch import run_bulk_eval

def run_single_evaluation() -> None:
    """Run the default evaluation using the repository input resume."""
    graph = build_graph()

    # Generate workflow visualization
    try:
        png = graph.get_graph().draw_mermaid_png()
        with open("ats_workflow.png", "wb") as f:
            f.write(png)
    except Exception as e:
        print(f"Warning: Could not generate workflow PNG: {e}")

    # Use resume_2 as default for single mode
    resume_path = Path("input/resume_2.pdf")
    jd_path = Path("data/jd.txt")

    print(f"Evaluating {resume_path}...")
    result = graph.invoke(
        {
            "resume_path": str(resume_path),
            "jd_path": str(jd_path),
        },
        config={"configurable": {"thread_id": "single_eval_test"}}
    )

    print("\n==============================")
    print("ATS EVALUATION RESULT")
    print("==============================")
    print(f"Verdict: {result.get('verdict', 'Unknown')}")
    print(f"Score: {result.get('result', {}).get('overall_score', 'N/A')}")
    print("==============================\n")

def main() -> None:
    """Main entry point with support for single and batch modes."""
    parser = argparse.ArgumentParser(description="ATS Recruiter Agent")
    parser.add_argument(
        "--mode",
        choices=["single", "batch"],
        default="single",
        help="Evaluation mode: 'single' for one resume, 'batch' for all pending applications of a job"
    )
    parser.add_argument(
        "--job-id",
        type=int,
        default=None,
        help="Job requisition id to bulk-evaluate (required for --mode batch)"
    )

    args = parser.parse_args()

    if args.mode == "batch":
        if args.job_id is None:
            parser.error("--job-id is required when --mode batch (use the API instead for the normal app flow: POST /jobs/{id}/evaluations)")
        run_bulk_eval(args.job_id)
    else:
        run_single_evaluation()

if __name__ == "__main__":
    main()
