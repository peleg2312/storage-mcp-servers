#!/usr/bin/env python3
"""The team GitLab token on the multi-user VM: paas-git-credential answers git's "get" for a host that has a token file
(username:token, or a bare token), nothing for any other host or action, and never treats the host as a path."""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HELPER = os.path.join(HERE, "multiuser", "paas-git-credential")
d = tempfile.mkdtemp()
open(os.path.join(d, "gitlab.example.com.token"), "w").write("paas:glpat-abc123\n")
open(os.path.join(d, "gl2:8443.token"), "w").write("glpat-bare\n")
os.makedirs(os.path.join(d, "x"))
open(os.path.join(d, "x", "evil.token"), "w").write("root:nope\n")


def ask(action, host):
    r = subprocess.run(["sh", HELPER, action], input=f"protocol=https\nhost={host}\npath=storage/brain-nas.git\n" if host else "",
                       capture_output=True, text=True, timeout=10, env=dict(os.environ, PAAS_GIT_DIR=d))
    assert r.returncode == 0, (r.returncode, r.stderr)
    return r.stdout


assert ask("get", "gitlab.example.com") == "username=paas\npassword=glpat-abc123\n"
assert ask("get", "gl2:8443") == "username=paas\npassword=glpat-bare\n"           # a bare token: any user name does for GitLab
assert ask("get", "github.com") == ""                                              # no token for that host: git tries the next helper
assert ask("get", "../x/evil") == "" and ask("get", "x/evil") == "" and ask("get", "") == ""
assert ask("store", "gitlab.example.com") == "" and ask("erase", "gitlab.example.com") == ""
# a token per repository (a project access token) wins over the host's when git hands the path over
open(os.path.join(d, "gitlab.example.com__storage__brain-nas.git.token"), "w").write("paas:glpat-nas-only\n")
assert ask("get", "gitlab.example.com") == "username=paas\npassword=glpat-nas-only\n"          # ask() sends path=storage/brain-nas.git
r = subprocess.run(["sh", HELPER, "get"], input="protocol=https\nhost=gitlab.example.com\npath=storage/brain-san.git\n",
                   capture_output=True, text=True, timeout=10, env=dict(os.environ, PAAS_GIT_DIR=d))
assert r.stdout == "username=paas\npassword=glpat-abc123\n", r.stdout                           # another repository: the host's token
r = subprocess.run(["sh", HELPER, "get"], input="protocol=https\nhost=gl2:8443\npath=../x/evil\n",
                   capture_output=True, text=True, timeout=10, env=dict(os.environ, PAAS_GIT_DIR=d))
assert r.stdout == "username=paas\npassword=glpat-bare\n", r.stdout                            # a path with .. is ignored, not followed
print("git credential helper ok")
sys.exit(0)
