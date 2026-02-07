#!/usr/bin/env python3
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {'.venv', '.git', '__pycache__', 'node_modules'}
BINARY_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.pyc', '.so', '.dll', '.exe', '.zip', '.tar', '.gz'}

def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDE_DIRS:
        return True
    if path.suffix.lower() in BINARY_EXTS:
        return True
    return False

def replace_text(text: str) -> str:
    pattern = re.compile(r"ProjectKiwi", re.IGNORECASE)
    def repl(m):
        # Always use ProjectKiwi as replacement casing
        return 'ProjectKiwi'
    return pattern.sub(repl, text)

def main():
    changed = []
    for root, dirs, files in os.walk(ROOT):
        # skip excluded dirs early
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in files:
            fpath = Path(root) / fname
            if should_skip(fpath):
                continue
            try:
                text = fpath.read_text(encoding='utf-8')
            except Exception:
                continue
            if re.search(r'ProjectKiwi', text, re.IGNORECASE):
                new = replace_text(text)
                if new != text:
                    fpath.write_text(new, encoding='utf-8')
                    changed.append(str(fpath.relative_to(ROOT)))
    print('Modified files:')
    for p in changed:
        print(p)

if __name__ == '__main__':
    main()
