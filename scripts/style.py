#!/usr/bin/env python3
"""Style lint for project prose: ontology labels and comments, docs and deliverable text.

Rules follow the writing conventions for CERTAIN project text:
no em dashes, and a list of expressions to avoid.

  python3 scripts/style.py deliverable/*.md docs/*.md
"""
from __future__ import annotations

import re
import sys

BANNED = [
    "delve", "underscore", "leverage", "facilitate", "notably", "importantly",
    "it is worth", "should be noted", "furthermore", "moreover", "in conclusion",
    "robust", "comprehensive", "seamless", "paradigm", "cutting-edge", "transformative",
    "holistic", "significantly", "various", "numerous", "a wide range of",
    "plays a crucial role", "serves as", "enables", "empowers",
    "demonstrates the importance of", "highlights", "sheds light on",
    "utilize", "utilise", "due to the fact that", "prior to", "subsequent to",
]
_PATTERNS = [(w, re.compile(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", re.I)) for w in BANNED]


def findings(text: str) -> list[str]:
    out = []
    if "—" in text:
        out.append("em dash")
    out += [f"'{w}'" for w, pat in _PATTERNS if pat.search(text)]
    return out


def main(paths) -> int:
    n = 0
    for path in paths:
        for i, line in enumerate(open(path, encoding="utf-8"), 1):
            if line.lstrip().startswith(("|", "```", "<!--")) and "—" not in line:
                continue
            f = findings(line)
            if f:
                n += 1
                print(f"{path}:{i}: {', '.join(f)}: {line.strip()[:100]}")
    print(f"{n} line(s) with style findings")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
