"""Token budgets: python3 brain/test_budgets.py (stdlib; parses sources, imports nothing)"""
import ast, glob, os, sys

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
C = os.path.join(R, "brain", "claude")
bad = []


def size(*p):
    return os.path.getsize(os.path.join(*p))


def front(path):
    t = open(path, encoding="utf-8").read().split("---")
    return len(t[1].encode()) if len(t) > 2 else 0


def check(label, got, cap):
    print(("ok   " if got <= cap else "FAIL ") + "%s: %d <= %d" % (label, got, cap))
    if got > cap:
        bad.append(label)


check("CLAUDE.md + persona.md + notes.md", size(C, "CLAUDE.md") + size(R, "brain", "teams", "san", "persona.md") + size(C, "brain", "notes.md"), 8 * 1024)
check("coding.md (read on demand by code work)", size(C, "brain", "coding.md"), 3 * 1024)
check("storage.md + environment.md + tool-map.md",
      sum(size(C, "brain", f) for f in ("storage.md", "environment.md", "tool-map.md")), 12 * 1024)
check("skill frontmatter total", sum(front(f) for f in glob.glob(C + "/skills/*/SKILL.md")), 10500)
check("agent frontmatter total", sum(front(f) for f in glob.glob(C + "/agents/*.md")), 3600)
# the same budgets per team profile (what one team's member pays): brain/plugin/build.py resolves each team's lists
import json, shutil, subprocess, tempfile
tmp = tempfile.mkdtemp()
for team in sorted(d for d in os.listdir(os.path.join(R, "brain", "teams")) if os.path.isfile(os.path.join(R, "brain", "teams", d, "team.json"))):
    subprocess.run([sys.executable, os.path.join(R, "brain", "plugin", "build.py"), tmp, "--team", team], check=True, stdout=subprocess.DEVNULL)
    P = os.path.join(tmp, "paas-brain-" + team)
    check(f"team {team}: CLAUDE.md + persona.md + notes.md", size(C, "CLAUDE.md") + size(P, "brain", "persona.md") + size(P, "brain", "notes.md"), 8 * 1024)
    check(f"team {team}: storage.md + environment.md + tool-map.md", sum(size(P, "brain", f) for f in ("storage.md", "environment.md", "tool-map.md")), 12 * 1024)
    check(f"team {team}: skill frontmatter total", sum(front(f) for f in glob.glob(P + "/skills/*/SKILL.md")), 10500)
    check(f"team {team}: agent frontmatter total", sum(front(f) for f in glob.glob(P + "/agents/*.md")), 3600)
shutil.rmtree(tmp, ignore_errors=True)
for f in ("powermax-mcp/server.py", "powerflex-mcp/server.py", "ucsc-mcp/server.py",
          "docs-search-mcp/server.py", "docs-search-mcp/mcp_stdio.py", "mds-mcp/entry.py"):
    for n in ast.parse(open(os.path.join(R, f), encoding="utf-8").read()).body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "INSTRUCTIONS":
            check(f + " INSTRUCTIONS", len(ast.literal_eval(n.value)), 4096)
sys.exit(1 if bad else 0)
