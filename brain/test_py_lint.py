"""Check of the ruff post-edit hook: python3 brain/test_py_lint.py (needs ruff on PATH or in ~/.claude/devtools-venv)"""
import json, os, shutil, subprocess, sys, tempfile

hook = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claude", "hooks", "py-lint.py")
if not (shutil.which("ruff") or os.path.exists(os.path.expanduser("~/.claude/devtools-venv/bin/ruff"))):
    sys.exit(print("py-lint: skipped (ruff not installed; sh brain/devtools/install-devtools.sh)"))
d = tempfile.mkdtemp()
files = {"bad.py": "import os\n\ndef f():\n    return undefined_name\n", "style.py": "import sys\nimport os\nprint(os, sys)\n",
         "notes.txt": "import os\n", "proj/pyproject.toml": '[tool.ruff.lint]\nselect = ["I"]\n',
         "proj/style.py": "import sys\nimport os\nprint(os, sys)\n"}
for n, t in files.items():
    os.makedirs(os.path.dirname(os.path.join(d, n)), exist_ok=True)
    open(os.path.join(d, n), "w").write(t)
run = lambda n: subprocess.run([sys.executable, hook], input=json.dumps({"tool_input": {"file_path": os.path.join(d, n)}}),
                               capture_output=True, text=True).stdout
out = run("bad.py")
assert "F821 Undefined name `undefined_name`" in out and "F401" in out and "I001" not in out, out
assert run("style.py") == "" and run("notes.txt") == ""           # no style nags without a config; not Python
assert "I001" in run("proj/style.py")                             # the project's own rules apply
print("py-lint ok")
