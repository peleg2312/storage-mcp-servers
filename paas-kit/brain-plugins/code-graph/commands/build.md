---
description: Build (or bring up to date) the code graph of this git repository
allowed-tools: Bash(paas-kit graph:*)
---
Build the code graph of the git repository we are in, then report its size.

1. Run `paas-kit graph build` (first time; a large code base can take a few minutes) — or, if
   `paas-kit graph status` already shows nodes, `paas-kit graph update` (only the changed files).
2. Run `paas-kit graph status` and tell the user in two lines: files, nodes, edges, and that the
   graph stays up to date by itself after edits made here (after `git pull`: /code-graph:build again).
