

from __future__ import annotations
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.orchestrator import FieldWiseOrchestrator, CaseReport  # noqa: E402

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "case_history.json")


def _report_to_dict(report: CaseReport) -> dict:
    return {
        "escalated": report.escalated,
        "category": report.category,
        "diagnosis": report.diagnosis,
        "explanation": report.explanation,
        "treatment_options": report.treatment_options,
        "next_check_date": report.next_check_date,
        "case_id": report.case_id,
        "trace": report.trace,
    }


def cmd_diagnose(args: argparse.Namespace) -> None:
    orchestrator = FieldWiseOrchestrator(llm_mode=args.llm_mode)
    report = orchestrator.process_case(
        description=args.description,
        farmer_id=args.farmer_id,
        region=args.region,
        image_path=args.image,
    )
    print(json.dumps(_report_to_dict(report), indent=2))


def cmd_batch(args: argparse.Namespace) -> None:
    with open(args.input, "r") as f:
        cases = json.load(f)

    orchestrator = FieldWiseOrchestrator(llm_mode=args.llm_mode)
    results = []
    for i, case in enumerate(cases):
        print(f"Processing case {i + 1}/{len(cases)} (farmer_id={case.get('farmer_id')})...", file=sys.stderr)
        report = orchestrator.process_case(
            description=case["description"],
            farmer_id=case["farmer_id"],
            region=case.get("region", "default"),
            image_path=case.get("image_path"),
        )
        results.append({"input": case, "report": _report_to_dict(report)})

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {len(results)} result(s) to {args.output}", file=sys.stderr)


def cmd_history(args: argparse.Namespace) -> None:
    if not os.path.exists(HISTORY_FILE):
        print("[]")
        return
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
    filtered = [h for h in history if h.get("farmer_id") == args.farmer_id]
    print(json.dumps(filtered, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fieldwise_cli",
        description="FieldWise Agent Skill — CLI for the crop health multi-agent pipeline.",
    )
    parser.add_argument(
        "--llm-mode",
        choices=["mock", "gemini"],
        default=None,
        help="Override FIELDWISE_LLM_MODE env var (default: mock).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_diagnose = subparsers.add_parser("diagnose", help="Run a single case through the pipeline.")
    p_diagnose.add_argument("--farmer-id", required=True)
    p_diagnose.add_argument("--description", required=True)
    p_diagnose.add_argument("--region", default="default")
    p_diagnose.add_argument("--image", default=None, help="Optional path to a crop photo.")
    p_diagnose.set_defaults(func=cmd_diagnose)

    p_batch = subparsers.add_parser("batch", help="Process many cases from a JSON file.")
    p_batch.add_argument("--input", required=True)
    p_batch.add_argument("--output", required=True)
    p_batch.set_defaults(func=cmd_batch)

    p_history = subparsers.add_parser("history", help="Show a farmer's past cases.")
    p_history.add_argument("--farmer-id", required=True)
    p_history.set_defaults(func=cmd_history)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
