"""Seed the bundled authority index on a fresh container volume only."""
import json
import os
from pathlib import Path

def main() -> None:
    target = Path(os.getenv("AUTHORITY_STORE_PATH", "data/authorities.json"))
    if target.exists():
        return
    root = Path(__file__).resolve().parent.parent / "data"
    bundled = []
    for source in (root / "authorities.example.json", root / "wto_authorities.json"):
        bundled.extend(json.loads(source.read_text(encoding="utf-8")))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(bundled, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
