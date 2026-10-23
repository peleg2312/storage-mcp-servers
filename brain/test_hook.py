"""Check of the read-only hook: python3 brain/test_hook.py"""
import importlib.util, os
spec = importlib.util.spec_from_file_location("h", os.path.join(os.path.dirname(__file__), "claude/hooks/block-write-tools.py"))
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
q = lambda sql: h.reason_for("mcp__kuparashit__execute_query", {"query": sql})
for ok in ["SELECT naa, host FROM paths WHERE wwpn LIKE '%10000090fa%'", "with t as (select 1) select * from t",
           "SELECT name, sql FROM sqlite_master", "PRAGMA table_info(paths)", "select updated_at, deleted from vms"]:
    assert q(ok) is None, ok
for bad in ["DELETE FROM vms", "select 1; delete from vms", "WITH t AS (SELECT 1) DELETE FROM vms WHERE 1",
            "insert or replace into x values(1)", "UPDATE vms SET name='x'", "ATTACH DATABASE 'x' AS y",
            "drop table paths", "PRAGMA journal_mode = wal"]:
    assert q(bad), bad
assert h.reason_for("mcp__ontap__lun_delete", {}) and h.reason_for("mcp__aria__get_alerts", {}) is None
for t in "overview locate related luns query aggregate history diff trend compare fields relationships sql export rescan".split():
    assert h.reason_for("mcp__kuparashit__" + t, {"where": "naas != not found"}) is None, t
print("hook ok")
