### How to use `scaffold_from_tree.py`

1. Put your tree snippet into `prompt_coach_tree.md` (just paste the fenced block).
2. Run:

```bash
python tools/scaffold_from_tree.py --from-file prompt_coach_tree.md --root . \
  --default-file-content ""
```

You’ll see actions like:

```
mkdir  /…/prompt-coach
touch  /…/prompt-coach/README.md
touch  /…/prompt-coach/pyproject.toml
mkdir  /…/prompt-coach/coach
touch  /…/prompt-coach/coach/__init__.py
…
```

* **Dry run first**:

```bash
python tools/scaffold_from_tree.py --from-file prompt_coach_tree.md --root . --dry-run
```

* **Overwrite existing files**:

```bash
python tools/scaffold_from_tree.py --from-file prompt_coach_tree.md --root . --force
```

**Notes**

* Works on macOS/Linux/Windows (uses `pathlib`).
* Treats any entry ending in `/` as a directory; everything else as a file.
* If you keep comments to the right of paths (e.g., `README.md  # docs`), it’ll strip them.
