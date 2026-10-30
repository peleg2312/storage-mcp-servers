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

# shell guard: development and reading pass, infrastructure changes are blocked, general changes ask first
sh = h.shell_check
for ok in ["oc get pvc -A", "kubectl describe pod csi-node-x -n vxflexos", "oc logs -f deploy/csi-controller",
           "oc exec pod-1 -- multipath -ll", "curl -sk -u mon:x https://u4p:8443/univmax/restapi/version",
           "curl -X POST http://localhost:8000/api/items -d '{}'", "curl -X DELETE http://127.0.0.1:8080/items/1",
           "ssh admin@mds01 'show zoneset active vsan 10'", "ssh admin@cl1 'volume show -fields size'",
           "scli --query_all_volumes", "sudo -u root symcfg list", "bash -c \"symcfg list\"",
           "chroot /host multipath -ll", "ssh host 'tail -n 50 /var/log/restart.log'", "symcfg list", "symaccess -sid 123 list view", "symdev -sid 123 show 00A1",
           "govc ls /dc/vm", "esxcli storage core path list", "multipath -ll", "iscsiadm -m session", "nvme list",
           "systemctl status multipathd", 'grep -rn "kubectl delete" docs', "echo hi > /tmp/x", "mount", "lsblk",
           "fdisk -l", "dd if=/dev/sda of=/tmp/mbr bs=512 count=1", "helm list -A", "cat /sys/class/fc_host/host1/port_name",
           "python3 -m pytest -q", "uvicorn app:app --reload", "git commit -m x && git push", "mkfs.ext4 /tmp/disk.img",
           "terraform plan", "ansible-playbook site.yml --check", "pip install -r requirements.txt"]:
    assert sh(ok)[0] is None, (ok, sh(ok))
for ask in ["oc apply -f deploy.yaml", "kubectl delete pod x", "oc rollout restart deploy/api", "helm upgrade app ./chart",
            "oc adm drain node1", "curl -X POST https://api.example.com/v1/x", "curl --data x https://u4p:8443/univmax/x",
            "systemctl restart myapp", "terraform apply", "ansible-playbook site.yml", "sudo oc delete pod x",
            "timeout 30 kubectl scale deploy/x --replicas=0", "FOO=1 oc delete x", "true && oc create ns x"]:
    assert sh(ask)[0] == "ask", (ask, sh(ask))
for bad in ["ssh admin@mds01 'conf t ; zone name z1 vsan 10'", "ssh admin@cl1 'volume delete -vserver s -volume v'",
            "ssh admin@cl1 lun mapping create -path /vol/v/l -igroup g", "scli --add_volume --size_gb 8",
            "scli --map_volume_to_sdc --volume_name v", "symconfigure -sid 1 -cmd 'x;' commit",
            "symaccess -sid 1 create view -name v", "symsg -sid 1 -sg SG add dev 00A1", "symsnapvx -sid 1 establish -name s",
            "govc vm.destroy vm1", "govc vm.power -off vm1", "esxcli storage core adapter rescan --all",
            "mkfs.xfs /dev/sdb", "wipefs -a /dev/sdb", "dd if=/dev/zero of=/dev/sdb bs=1M", "multipath -f mpatha",
            "iscsiadm -m node --login", "nvme disconnect -n nqn.x", "echo 1 > /sys/block/sdb/device/delete",
            "echo '- - -' | tee /sys/class/scsi_host/host0/scan", "oc exec pod-1 -- multipath -f mpatha",
            "sudo wipefs -a /dev/sdc", "sudo -u root symsg -sid 1 create foo", "sudo -g wheel symsg delete x",
            "xargs -a f symsg delete", "timeout -s KILL 5 symconfigure commit", "bash -c \"symsg create foo\"",
            "sh -c 'symconfigure -cmd x commit'", "eval \"symsg create foo\"", "eval symsg create foo",
            "bash -c \"echo hi; symsg create foo\"", "cd /x && sudo bash -lc 'multipath -f x'",
            "chroot /host multipath -f x", "oc debug node/x -- chroot /host multipath -f x",
            "oc debug node/x -- chroot /host sh -c 'multipath -F'", "$(ssh admin@mds 'copy run start')", "rescan-scsi-bus.sh -r"]:
    assert sh(bad)[0] == "block", (bad, sh(bad))
print("shell guard ok")

# databases MCP: writes are asked (the user confirms), reads pass, write SQL through the read tool stays blocked
import io, json as _j, sys as _s
def run_hook(payload):
    old = _s.stdin, _s.stdout
    _s.stdin, _s.stdout = io.StringIO(_j.dumps(payload)), io.StringIO()
    try:
        rc = h.main(); out = _s.stdout.getvalue()
    finally:
        _s.stdin, _s.stdout = old
    return rc, out
rc, out = run_hook({"tool_name": "mcp__databases__pg_execute", "tool_input": {"connection": "dev", "sql": "DELETE FROM t"}})
assert rc == 0 and '"ask"' in out and "DELETE FROM t" in out, out
rc, out = run_hook({"tool_name": "mcp__databases__mongo_write", "tool_input": {"connection": "dev", "op": "insert_one"}})
assert rc == 0 and '"ask"' in out, out
assert run_hook({"tool_name": "mcp__databases__pg_query", "tool_input": {"sql": "SELECT 1"}}) == (0, "")
assert h.reason_for("mcp__databases__pg_query", {"sql": "DROP TABLE t"})
for q_ in ("symaccess create view masking view", "how to grant access to a vserver", "update volume set autosize"):
    for t_ in ("mcp__docs-local__search_docs", "mcp__docs-search__search_docs"):
        assert run_hook({"tool_name": t_, "tool_input": {"query": q_}}) == (0, ""), (t_, q_)
assert h.reason_for("mcp__databases__pg_query", {"query": "grant all on t to x"})    # databases keep the SQL check
long_ = "select 1; " + "x" * 2000 + "; drop table users"
out = run_hook({"tool_name": "mcp__databases__pg_execute", "tool_input": {"connection": "dev", "sql": long_}})[1]
assert "LONG/DESTRUCTIVE" in out and "more chars not shown" in out, out
print("databases guard ok")

# Bypass mode: the guard's questions are skipped (the user approved changes on the server); the blocks stay
BP = {"permission_mode": "bypassPermissions"}
assert run_hook({"tool_name": "Bash", "tool_input": {"command": "kubectl delete pod x"}, **BP}) == (0, "")
assert run_hook({"tool_name": "mcp__databases__pg_execute", "tool_input": {"connection": "dev", "sql": "DELETE FROM t"}, **BP}) == (0, "")
_s.stderr, _err = io.StringIO(), _s.stderr
try:
    assert run_hook({"tool_name": "Bash", "tool_input": {"command": "symconfigure -sid 1 commit"}, **BP})[0] == 2
    assert run_hook({"tool_name": "mcp__ontap__create_volume", "tool_input": {}, **BP})[0] == 2
finally:
    _s.stderr = _err
assert '"ask"' in run_hook({"tool_name": "Bash", "tool_input": {"command": "kubectl delete pod x"}})[1]
print("bypass guard ok")
