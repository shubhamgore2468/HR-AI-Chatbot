from pathlib import Path

def save_to_markdown(content: str, filename: str):
    """Save content to markdown file in output directory"""
    current_dir = Path(__file__).parent
    output_dir = current_dir.parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    filepath = output_dir / filename
    with filepath.open("w", encoding='utf-8') as f:
        f.write(content)
