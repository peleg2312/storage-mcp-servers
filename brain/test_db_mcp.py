"""Integration check of the read-only databases MCP against real servers:
    DB_MCP_TEST_PG=postgresql://postgres:pw@localhost:55432/appdb DB_MCP_TEST_MONGO=mongodb://localhost:57017 \
    <python with psycopg + pymongo> brain/test_db_mcp.py
(e.g. docker run -d -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=appdb -p 55432:5432 postgres:16; docker run -d -p 57017:27017 mongo:7)
Skips without those variables. Seeds sample data, calls every tool over stdio JSON-RPC, then tries to write."""
import json, os, subprocess, sys, tempfile

PG, MG = os.environ.get("DB_MCP_TEST_PG"), os.environ.get("DB_MCP_TEST_MONGO")
if not (PG and MG):
    sys.exit(print("db-mcp: SKIPPED, NOT RUN: the read-only guard was not tested (set DB_MCP_TEST_PG and DB_MCP_TEST_MONGO)", file=sys.stderr))
import psycopg, pymongo  # noqa: E402

with psycopg.connect(PG, autocommit=True) as c:                      # seed (the test, not the server, writes)
    c.execute("DROP TABLE IF EXISTS users, notes; CREATE SEQUENCE IF NOT EXISTS s1")
    c.execute("CREATE TABLE users (id serial PRIMARY KEY, email text UNIQUE NOT NULL, created timestamptz DEFAULT now())")
    c.execute("INSERT INTO users (email) SELECT 'u' || g || '@x.io' FROM generate_series(1, 30) g")
mc = pymongo.MongoClient(MG)
mc.shop.orders.drop()
mc.shop.orders.insert_many([{"sku": f"A{i % 3}", "qty": i, "addr": {"city": "TLV"}} for i in range(12)])
mc.shop.orders.create_index("sku")

conf = os.path.join(tempfile.mkdtemp(), "databases.json")
json.dump({"app-pg": {"type": "postgres", "uri": PG}, "shop": {"type": "mongo", "uri_env": "T_MONGO"},
           "dev-pg": {"type": "postgres", "uri": PG, "write": True},
           "dev-shop": {"type": "mongo", "uri": MG, "write": True}}, open(conf, "w"))
srv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claude", "tools", "db_mcp.py")
calls = [("db_list", {}), ("pg_schema", {"connection": "app-pg"}), ("pg_schema", {"connection": "app-pg", "table": "users"}),
         ("pg_query", {"connection": "app-pg", "sql": "SELECT id, email FROM users ORDER BY id", "limit": 5}),
         ("pg_explain", {"connection": "app-pg", "sql": "SELECT * FROM users WHERE email = 'u1@x.io'"}),
         ("pg_query", {"connection": "app-pg", "sql": "DELETE FROM users"}),
         ("pg_query", {"connection": "app-pg", "sql": "SELECT 1; DROP TABLE users"}),
         ("pg_query", {"connection": "app-pg", "sql": "CREATE TABLE evil (x int)"}),
         ("pg_query", {"connection": "app-pg", "sql": "SELECT nextval('s1')"}),
         ("mongo_schema", {"connection": "shop"}), ("mongo_schema", {"connection": "shop", "database": "shop"}),
         ("mongo_schema", {"connection": "shop", "database": "shop", "collection": "orders"}),
         ("mongo_find", {"connection": "shop", "database": "shop", "collection": "orders", "filter": '{"sku": "A1"}',
                         "sort": {"qty": -1}, "limit": 2}),
         ("mongo_count", {"connection": "shop", "database": "shop", "collection": "orders", "filter": {"sku": "A0"}}),
         ("mongo_aggregate", {"connection": "shop", "database": "shop", "collection": "orders",
                              "pipeline": [{"$group": {"_id": "$sku", "n": {"$sum": 1}}}, {"$sort": {"_id": 1}}]}),
         ("mongo_aggregate", {"connection": "shop", "database": "shop", "collection": "orders",
                              "pipeline": [{"$match": {}}, {"$out": "stolen"}]}),
         ("mongo_aggregate", {"connection": "shop", "database": "shop", "collection": "orders",
                              "pipeline": '[{"$merge": {"into": "x"}}]'}),
         ("pg_query", {"connection": "nope", "sql": "SELECT 1"}),
         # writes: refused on read-only connections, done on writable ones
         ("pg_execute", {"connection": "app-pg", "sql": "DELETE FROM users"}),
         ("pg_execute", {"connection": "dev-pg", "sql": "INSERT INTO users (email) VALUES ('new@x.io') RETURNING id, email"}),
         ("pg_execute", {"connection": "dev-pg", "sql": "CREATE TABLE notes (id int)"}),
         ("pg_execute", {"connection": "dev-pg", "sql": "INSERT INTO nothere VALUES (1)"}),
         ("mongo_write", {"connection": "shop", "database": "shop", "collection": "orders", "op": "insert_one", "document": {"sku": "Z"}}),
         ("mongo_write", {"connection": "dev-shop", "database": "shop", "collection": "orders", "op": "insert_one",
                          "document": '{"sku": "Z9", "qty": 99}'}),
         ("mongo_write", {"connection": "dev-shop", "database": "shop", "collection": "orders", "op": "update_many",
                          "filter": {"sku": "A0"}, "update": {"$set": {"flag": True}}}),
         ("mongo_write", {"connection": "dev-shop", "database": "shop", "collection": "orders", "op": "delete_many", "filter": {}}),
         ("mongo_write", {"connection": "dev-shop", "database": "shop", "collection": "orders", "op": "delete_one", "filter": {"sku": "Z9"}}),
         ("mongo_write", {"connection": "dev-shop", "database": "shop", "collection": "orders", "op": "create_index",
                          "keys": {"qty": 1}}),
         ("db_list", {}),
         # several statements in one string must never run (SET TRANSACTION READ WRITE would lift READ ONLY)
         ("pg_query", {"connection": "app-pg", "sql": "SET TRANSACTION READ WRITE; DELETE FROM users; COMMIT"}),
         ("pg_query", {"connection": "app-pg", "sql": "SELECT 1; SET TRANSACTION READ WRITE; DELETE FROM users; COMMIT"}),
         ("pg_explain", {"connection": "app-pg", "sql": "SELECT 1; SET TRANSACTION READ WRITE; DELETE FROM users; COMMIT"}),
         ("pg_query", {"connection": "app-pg", "sql": "SELECT id FROM users LIMIT 2;"}),
         ("pg_schema", {"connection": "app-pg", "table": "public.users"}),
         ("pg_schema", {"connection": "app-pg", "table": "nothere"})]
msgs = [{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"}, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}]
msgs += [{"jsonrpc": "2.0", "id": i + 10, "method": "tools/call", "params": {"name": n, "arguments": a}} for i, (n, a) in enumerate(calls)]
out = subprocess.run([sys.executable, srv], input="\n".join(json.dumps(m) for m in msgs) + "\n", capture_output=True, text=True,
                     env={**os.environ, "DB_MCP_CONFIG": conf, "T_MONGO": MG}, timeout=120).stdout
R = {r["id"]: r["result"] for r in map(json.loads, out.splitlines())}
assert len(R[1]["tools"]) == 10
assert {t["name"] for t in R[1]["tools"] if not t["annotations"].get("readOnlyHint")} == {"pg_execute", "mongo_write"}
res = lambda i: (R[i + 10]["isError"], R[i + 10]["content"][0]["text"])                   # noqa: E731
J = lambda i: json.loads(res(i)[1])                                                          # noqa: E731
assert ":pw@" not in res(0)[1] and "postgres@localhost" in res(0)[1], res(0)                # no password shown
assert any(r[1] == "users" for r in J(1)["rows"]), J(1)
t = J(2); assert [c[0] for c in t["columns"]] == ["id", "email", "created"] and any("PRIMARY KEY" in c[2] for c in t["constraints"]), t
q = J(3); assert q["rows"][0] == [1, "u1@x.io"] and len(q["rows"]) == 5 and "truncated" in q, q
assert "users_email_key" in J(4)["plan"] or "Index" in J(4)["plan"], J(4)
for i in (5, 6, 7, 8):                                                                       # every write refused
    err, text = res(i)
    assert err and ("read-only" in text or "read only" in text or "multiple commands" in text), (i, text)
assert J(9)["databases"] == ["shop"] and J(10)["collections"][0]["documents_estimate"] == 12
s = J(11); assert s["fields"]["addr.city"] == {"str": 12} and any(ix["key"] == {"sku": 1} for ix in s["indexes"]), s
f = J(12)["documents"]; assert [d["qty"] for d in f] == [10, 7] and isinstance(f[0]["_id"], str), f
assert J(13)["count"] == 4 and J(14)["documents"][0] == {"_id": "A0", "n": 4}
assert res(15)[0] and "$out" in res(15)[1] and res(16)[0] and "$merge" in res(16)[1]
assert res(17)[0] and "unknown connection" in res(17)[1]
assert res(18)[0] and "read-only" in res(18)[1] and 'write": true' in res(18)[1].replace("\\", ""), res(18)
w = J(19); assert w["rowcount"] == 1 and w["rows"][0][1] == "new@x.io", w                     # INSERT ... RETURNING
assert J(20)["status"] == "CREATE TABLE" and res(21)[0] and "nothere" in res(21)[1]
assert res(22)[0] and "read-only" in res(22)[1]                                               # read-only Mongo connection
assert len(J(23)["inserted_id"]) == 24 and J(24) == {"matched": 4, "modified": 4, "upserted_id": None}
assert res(25)[0] and "all=true" in res(25)[1] and J(26)["deleted"] == 1 and J(27)["index"] == "qty_1"
assert [(c["connection"], c["write"]) for c in J(28)["connections"]] == [("app-pg", False), ("shop", False), ("dev-pg", True), ("dev-shop", True)]
for i in (29, 30, 31):
    err, text = res(i)
    assert err and "multiple commands" in text, (i, text)
assert not res(32)[0] and len(J(32)["rows"]) == 2                                            # a trailing ; is fine
assert [c[0] for c in J(33)["columns"]] == ["id", "email", "created"] and res(34)[0] and "no such table" in res(34)[1]
with psycopg.connect(PG) as c:                                                              # only the writable connection changed it
    assert c.execute("SELECT count(*) FROM users").fetchone()[0] == 31
    assert c.execute("SELECT to_regclass('notes')").fetchone()[0] == "notes"
    assert c.execute("SELECT to_regclass('evil')").fetchone()[0] is None
assert "stolen" not in mc.shop.list_collection_names() and "x" not in mc.shop.list_collection_names()
assert mc.shop.orders.count_documents({}) == 12 and mc.shop.orders.count_documents({"flag": True}) == 4
print("db-mcp ok")
