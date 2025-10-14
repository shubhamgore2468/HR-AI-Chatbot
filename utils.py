from pathlib import Path

def print_out_md(filepath: Path, result: dict):
    out_dir = Path("./output")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "final_results.md"

    lines = []
    lines.append("# Final Results\n")
    for i, msg in enumerate(result.get("messages", []), start=1):
        role = msg.__class__.__name__ if hasattr(msg, "__class__") else "Message"
        content = getattr(msg, "content", str(msg))
        lines.append(f'##Message {i} - {role}\n')
        lines.append(content + "\n")

    out_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote final results to {out_file.resolve()}")   