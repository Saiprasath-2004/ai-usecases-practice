"""Command-line entry point for running a resume ATS evaluation."""

from pathlib import Path

from ats_agent.graph.builder import build_graph


def main() -> None:
    """Run the default evaluation using the repository input resume."""

    graph = build_graph()

    resume_path = Path("input/resume.pdf")
    jd_path = Path("data/jd.txt")

    result = graph.invoke(
        {
            "resume_path": str(resume_path),
            "jd_path": str(jd_path),
        }
    )

    print("\n==============================")
    print("ATS EVALUATION")
    print("==============================")
    print(result["result"])


if __name__ == "__main__":
    main()