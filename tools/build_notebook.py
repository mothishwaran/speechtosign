"""Assemble Speech_to_ISL_Project.ipynb from the part files.

Run from the project root:
    python tools/build_notebook.py
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())

# Importing the parts appends to the shared CELLS list, in order.
from tools.build_notebook_part1 import CELLS  # noqa: E402
import tools.build_notebook_part2  # noqa: F401,E402
import tools.build_notebook_part3  # noqa: F401,E402

OUT = "Speech_to_ISL_Project.ipynb"


def to_source(text):
    """nbformat wants a list of lines, each keeping its trailing newline."""
    lines = text.split("\n")
    return [ln + "\n" for ln in lines[:-1]] + [lines[-1]]


def main():
    cells = []
    for i, (kind, text) in enumerate(CELLS):
        cell_id = f"cell-{i:03d}"          # nbformat 4.5 requires stable ids
        if kind == "markdown":
            cells.append({
                "cell_type": "markdown",
                "id": cell_id,
                "metadata": {},
                "source": to_source(text),
            })
        else:
            cells.append({
                "cell_type": "code",
                "id": cell_id,
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": to_source(text),
            })

    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3 (.venv)",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11.1"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)

    n_md = sum(1 for k, _ in CELLS if k == "markdown")
    n_code = sum(1 for k, _ in CELLS if k == "code")
    size_kb = os.path.getsize(OUT) / 1024
    print(f"wrote {OUT}")
    print(f"  {len(cells)} cells  ({n_md} markdown, {n_code} code)")
    print(f"  {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
