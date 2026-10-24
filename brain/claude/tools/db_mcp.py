#!/usr/bin/env python3
"""MCP server (stdio) for PostgreSQL and MongoDB: lets Claude read real schemas and data while it writes API
code, and change data / schema on connections marked writable. Registered by brain/install.sh as "databases".

Connections: ~/.claude/brain/databases.json (re-read on every call, so edits need no restart), e.g.
  {"app-pg":    {"type": "postgres", "uri": "postgresql://app_ro@pg01.corp:5432/appdb"},
   "dev-pg":    {"type": "postgres", "uri": "postgresql://app@localhost/appdb_dev", "write": true},
   "app-mongo": {"type": "mongo",    "uri_env": "APP_MONGO_URI"}}
Passwords never in that file: Postgres reads ~/.pgpass (chmod 600), a Mongo URI with a password comes from the
environment variable named in uri_env. Use database accounts with read rights only.

Reading tools are read-only by construction on every connection: each Postgres statement runs in a READ ONLY
transaction (statement_timeout 15 s) and is rolled back; Mongo reads are find / aggregate (no $out, $merge) /
count / list / indexes. Writing (pg_execute, mongo_write) works only on connections with "write": true, and the
brain's hook asks the user to confirm each write call. Results are capped (rows, long values cut).
Drivers: psycopg (3) and pymongo, installed with the dev tools (brain/devtools); a missing driver only disables
its database type.
"""
import datetime
import decimal
import json
import os
import re
import sys
import uuid

CONFIG = os.environ.get("DB_MCP_CONFIG") or os.path.expanduser("~/.claude/brain/databases.json")
TIMEOUT_MS = 15000
MAX_ROWS, MAX_VALUE = 500, 400


def connections():
    try:
        conf = json.load(open(CONFIG))
    except FileNotFoundError:
        raise ValueError(f"no connections yet: create {CONFIG} (see the db_list tool description)")
    return {k: v for k, v in conf.items() if isinstance(v, dict)}


def conn_spec(name, kind):
    conf = connections()
    if name not in conf:
        raise ValueError(f"unknown connection {name!r}; configured: {', '.join(conf) or 'none'}")
    c = conf[name]
    if c.get("type") != kind:
        raise ValueError(f"{name} is a {c.get('type')} connection, not {kind}")
    uri = c.get("uri") or os.environ.get(c.get("uri_env", ""), "")
    if not uri:
        raise ValueError(f"{name}: no uri, and environment variable {c.get('uri_env')!r} is empty")
    return uri


def writable(name):
    if connections().get(name, {}).get("write") is not True:
        raise PermissionError(f"{name} is read-only: add \"write\": true to it in {CONFIG} to allow changes")


def clean(v):
    """JSON-safe, short: long strings and binary cut, dates / decimals / ids as text."""
    if isinstance(v, (bytes, bytearray, memoryview)):
        return f"<{len(bytes(v))} bytes>"
    if isinstance(v, str):
        return v if len(v) <= MAX_VALUE else v[:MAX_VALUE] + f"... ({len(v)} chars)"
    if isinstance(v, (datetime.date, datetime.datetime, datetime.time, decimal.Decimal, uuid.UUID)):
        return str(v)
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v[:50]] + ([f"... {len(v) - 50} more"] if len(v) > 50 else [])
    if v is None or isinstance(v, (bool, int, float)):
        return v
    return str(v)                                             # ObjectId, Decimal128, Timestamp...


# ---------------------------------------------------------------- PostgreSQL
def pg(name, write=False):
    import psycopg
    ro = "" if write else "-c default_transaction_read_only=on "
    conn = psycopg.connect(conn_spec(name, "postgres"), connect_timeout=10, autocommit=False,
                           options=f"{ro}-c statement_timeout={TIMEOUT_MS}")
    conn.read_only = not write
    return conn


def pg_rows(name, sql, params=None, limit=MAX_ROWS):
    with pg(name) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if cur.description is None:
                    return {"columns": [], "rows": [], "note": "statement returned no rows"}
                cols = [d.name for d in cur.description]
                rows = cur.fetchmany(limit + 1)
                more = len(rows) > limit
                return {"columns": cols, "rows": [[clean(v) for v in r] for r in rows[:limit]],
                        **({"truncated": f"first {limit} rows"} if more else {})}
        finally:
            conn.rollback()


def pg_schema(args):
    name, schema, table = args["connection"], args.get("schema") or "", args.get("table") or ""
    if not table:
        return pg_rows(name, """SELECT n.nspname AS schema, c.relname AS table, c.reltuples::bigint AS rows_estimate,
               pg_size_pretty(pg_total_relation_size(c.oid)) AS size
               FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE c.relkind IN ('r', 'p', 'v', 'm') AND n.nspname NOT IN ('pg_catalog', 'information_schema')
                 AND n.nspname NOT LIKE 'pg_toast%%' AND (%(s)s = '' OR n.nspname = %(s)s)
               ORDER BY 1, 2""", {"s": schema}, 1000)
    schema = schema or "public"
    p = {"s": schema, "t": table}
    return {"table": f"{schema}.{table}",
            "columns": pg_rows(name, """SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns WHERE table_schema = %(s)s AND table_name = %(t)s
                ORDER BY ordinal_position""", p)["rows"],
            "constraints": pg_rows(name, """SELECT con.conname, con.contype, pg_get_constraintdef(con.oid)
                FROM pg_constraint con JOIN pg_class c ON c.oid = con.conrelid JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %(s)s AND c.relname = %(t)s""", p)["rows"],
            "indexes": pg_rows(name, "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = %(s)s AND tablename = %(t)s",
                               p)["rows"]}


def pg_query(args):
    return pg_rows(args["connection"], args["sql"], None, max(1, min(int(args.get("limit", 100)), MAX_ROWS)))


def pg_execute(args):
    """Any SQL (INSERT / UPDATE / DELETE / DDL), committed; rows of RETURNING / SELECT parts come back."""
    name = args["connection"]
    writable(name)
    with pg(name, write=True) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(args["sql"])
                out = {"status": cur.statusmessage, "rowcount": cur.rowcount}
                if cur.description is not None:
                    rows = cur.fetchmany(MAX_ROWS)
                    out.update(columns=[d.name for d in cur.description], rows=[[clean(v) for v in r] for r in rows])
            conn.commit()
            return out
        except Exception:
            conn.rollback()
            raise


def pg_explain(args):
    out = pg_rows(args["connection"], "EXPLAIN (FORMAT TEXT) " + args["sql"], None, 300)
    return {"plan": "\n".join(r[0] for r in out["rows"])}


# ---------------------------------------------------------------- MongoDB
WRITE_STAGES = {"$out", "$merge"}


def mongo(name):
    import pymongo
    return pymongo.MongoClient(conn_spec(name, "mongo"), serverSelectionTimeoutMS=10000, socketTimeoutMS=TIMEOUT_MS,
                               readPreference="secondaryPreferred", appname="claude-db-mcp")


def doc_obj(v, field):
    if isinstance(v, str):
        try:
            v = json.loads(v) if v.strip() else {}
        except json.JSONDecodeError:
            raise ValueError(f"{field} must be JSON")
    return v


def field_types(docs, prefix="", out=None):
    """field path -> {type: count} over sample documents (nested documents flattened with dots)."""
    out = {} if out is None else out
    for d in docs:
        for k, v in d.items():
            path = f"{prefix}{k}"
            t = type(v).__name__
            out.setdefault(path, {}).setdefault(t, 0)
            out[path][t] += 1
            if isinstance(v, dict) and prefix.count(".") < 3:
                field_types([v], path + ".", out)
    return out


def mongo_schema(args):
    name, db, coll = args["connection"], args.get("database") or "", args.get("collection") or ""
    with mongo(name) as cl:
        if not db:
            return {"databases": [d for d in cl.list_database_names() if d not in ("admin", "local", "config")]}
        d = cl[db]
        if not coll:
            return {"database": db, "collections": [
                {"name": n, "documents_estimate": d[n].estimated_document_count(maxTimeMS=TIMEOUT_MS)}
                for n in sorted(d.list_collection_names())]}
        n = max(1, min(int(args.get("sample", 50)), 500))
        docs = list(d[coll].aggregate([{"$sample": {"size": n}}], maxTimeMS=TIMEOUT_MS))
        return {"collection": f"{db}.{coll}", "sampled": len(docs),
                "fields": {k: v for k, v in sorted(field_types(docs).items())},
                "indexes": [clean(ix) for ix in d[coll].list_indexes()]}


def mongo_find(args):
    lim = max(1, min(int(args.get("limit", 20)), MAX_ROWS))
    with mongo(args["connection"]) as cl:
        cur = cl[args["database"]][args["collection"]].find(
            doc_obj(args.get("filter") or {}, "filter"), doc_obj(args.get("projection"), "projection") or None,
            max_time_ms=TIMEOUT_MS).limit(lim)
        if args.get("sort"):
            cur = cur.sort(list(doc_obj(args["sort"], "sort").items()))
        return {"documents": [clean(x) for x in cur]}


def mongo_aggregate(args):
    pipeline = doc_obj(args["pipeline"], "pipeline")
    if not isinstance(pipeline, list):
        raise ValueError("pipeline must be a JSON list of stages")
    bad = re.findall(r'"(\$out|\$merge)"', json.dumps(pipeline))
    if bad:
        raise ValueError(f"read-only: {bad[0]} writes data and is not allowed")
    lim = max(1, min(int(args.get("limit", 50)), MAX_ROWS))
    with mongo(args["connection"]) as cl:
        rows = cl[args["database"]][args["collection"]].aggregate(pipeline + [{"$limit": lim}], maxTimeMS=TIMEOUT_MS)
        return {"documents": [clean(x) for x in rows]}


def mongo_count(args):
    with mongo(args["connection"]) as cl:
        return {"count": cl[args["database"]][args["collection"]].count_documents(
            doc_obj(args.get("filter") or {}, "filter"), maxTimeMS=TIMEOUT_MS)}


MONGO_OPS = {"insert_one", "insert_many", "update_one", "update_many", "replace_one", "delete_one", "delete_many",
             "create_index", "drop_index", "drop_collection"}


def mongo_write(args):
    """One write operation: op + the JSON fields it needs (document / documents / filter / update / keys / name)."""
    name, op = args["connection"], args.get("op", "")
    writable(name)
    if op not in MONGO_OPS:
        raise ValueError(f"op must be one of {sorted(MONGO_OPS)}")
    j = lambda k, d=None: doc_obj(args.get(k, d), k)                                      # noqa: E731
    with mongo(name) as cl:
        c = cl[args["database"]][args["collection"]]
        if op == "insert_one":
            return {"inserted_id": str(c.insert_one(j("document")).inserted_id)}
        if op == "insert_many":
            return {"inserted": len(c.insert_many(j("documents")).inserted_ids)}
        if op in ("update_one", "update_many"):
            r = getattr(c, op)(j("filter", {}), j("update"), upsert=bool(args.get("upsert")))
            return {"matched": r.matched_count, "modified": r.modified_count, "upserted_id": clean(r.upserted_id)}
        if op == "replace_one":
            r = c.replace_one(j("filter", {}), j("document"), upsert=bool(args.get("upsert")))
            return {"matched": r.matched_count, "modified": r.modified_count}
        if op in ("delete_one", "delete_many"):
            if op == "delete_many" and not j("filter", {}) and not args.get("all"):
                raise ValueError("delete_many with an empty filter deletes everything: pass all=true to mean it")
            return {"deleted": getattr(c, op)(j("filter", {})).deleted_count}
        if op == "create_index":
            return {"index": c.create_index(list(j("keys").items()), unique=bool(args.get("unique")))}
        if op == "drop_index":
            c.drop_index(args["name"])
            return {"dropped": args["name"]}
        c.drop()
        return {"dropped": f"{args['database']}.{args['collection']}"}


def db_list(args):
    out = []
    for n, c in connections().items():
        uri = c.get("uri") or os.environ.get(c.get("uri_env", ""), "")
        out.append({"connection": n, "type": c.get("type"), "write": c.get("write") is True,
                    "target": re.sub(r"//([^:@/]*):[^@/]*@", r"//\1@", uri) or f"(env {c.get('uri_env')} not set)"})
    return {"connections": out, "config": CONFIG}


# ---------------------------------------------------------------- MCP (stdio JSON-RPC)
RO = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True}
RW = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": True}
WRITE_TOOLS = {"pg_execute", "mongo_write"}
S = lambda **p: {"type": "object", "properties": p, "required": [k for k, v in p.items() if v.pop("req", False)]}  # noqa
STR, INT, ANY = (lambda req=False, d="": {"type": "string", "description": d, "req": req}), \
    (lambda d="": {"type": "integer", "description": d}), (lambda d="": {"description": d})
TOOLS = [
    ("db_list", db_list, "The configured database connections (name, type, host / db without password). Start here. "
     f"Connections live in {CONFIG}: {{name: {{type: postgres | mongo, uri | uri_env}}}}; Postgres passwords in ~/.pgpass.",
     S()),
    ("pg_schema", pg_schema, "PostgreSQL schema: without table, every table / view with row estimate and size; with "
     "table, its columns, constraints (PK / FK / unique / check) and indexes.",
     S(connection=STR(True), schema=STR(d="default: all (list) / public (table)"), table=STR())),
    ("pg_query", pg_query, "Run one read-only SQL statement (SELECT / WITH / SHOW) in a READ ONLY transaction, "
     f"15 s timeout, rolled back; up to {MAX_ROWS} rows (limit, default 100).",
     S(connection=STR(True), sql=STR(True), limit=INT())),
    ("pg_execute", pg_execute, "Change data or schema on a WRITABLE connection (\"write\": true): INSERT / UPDATE / "
     "DELETE / CREATE / ALTER ..., committed; RETURNING rows come back. Prefer the app's migrations for lasting schema "
     "changes. The user confirms each call.", S(connection=STR(True), sql=STR(True))),
    ("pg_explain", pg_explain, "EXPLAIN (not ANALYZE) of a query: the plan, indexes used, estimated rows.",
     S(connection=STR(True), sql=STR(True))),
    ("mongo_schema", mongo_schema, "MongoDB schema: no database -> databases; database -> collections with document "
     "estimates; collection -> field paths with types and counts from a random sample (sample, default 50) and indexes.",
     S(connection=STR(True), database=STR(), collection=STR(), sample=INT())),
    ("mongo_find", mongo_find, "find() with a JSON filter / projection / sort (e.g. {\"status\": \"active\"}); "
     "limit default 20.", S(connection=STR(True), database=STR(True), collection=STR(True), filter=ANY(),
                            projection=ANY(), sort=ANY(), limit=INT())),
    ("mongo_aggregate", mongo_aggregate, "aggregate() with a JSON pipeline list ($out / $merge refused); limit "
     "default 50.", S(connection=STR(True), database=STR(True), collection=STR(True), pipeline=ANY(), limit=INT())),
    ("mongo_count", mongo_count, "count_documents() with a JSON filter.",
     S(connection=STR(True), database=STR(True), collection=STR(True), filter=ANY())),
    ("mongo_write", mongo_write, "One write on a WRITABLE connection (\"write\": true). op: insert_one (document), "
     "insert_many (documents), update_one / update_many (filter, update, upsert), replace_one (filter, document), "
     "delete_one / delete_many (filter; an empty filter needs all=true), create_index (keys, unique), drop_index "
     "(name), drop_collection. The user confirms each call.",
     S(connection=STR(True), database=STR(True), collection=STR(True), op=STR(True), document=ANY(), documents=ANY(),
       filter=ANY(), update=ANY(), upsert={"type": "boolean"}, keys=ANY(), unique={"type": "boolean"}, name=STR(),
       all={"type": "boolean"})),
]
FUNCS = {n: f for n, f, _, _ in TOOLS}
INSTRUCTIONS = ("The user's PostgreSQL and MongoDB databases, for writing and checking API code against the real schema "
                "and data. db_list first (it shows which connections are writable); pg_schema / mongo_schema before "
                "writing queries or models. Reading tools never change anything. pg_execute / mongo_write change data on "
                "writable connections only, each confirmed by the user: say what you will change and why first, prefer "
                "the app's migrations for lasting schema changes, never write to a connection the user calls production. "
                "Never paste secrets; show what you ran and its result.")


def handle(msg):
    method, params, mid = msg.get("method"), msg.get("params") or {}, msg.get("id")
    if method == "initialize":
        return {"protocolVersion": params.get("protocolVersion", "2025-06-18"), "capabilities": {"tools": {}},
                "serverInfo": {"name": "databases", "version": "1.0"}, "instructions": INSTRUCTIONS}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": [{"name": n, "description": d, "inputSchema": s, "annotations": RW if n in WRITE_TOOLS else RO}
                          for n, _, d, s in TOOLS]}
    if method == "tools/call":
        try:
            out = FUNCS[params["name"]](params.get("arguments") or {})
            return {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False, default=str)}], "isError": False}
        except Exception as e:
            msg_ = str(e).split("\n")[0][:500]
            return {"content": [{"type": "text", "text": f"{e.__class__.__name__}: {msg_}"}], "isError": True}
    if mid is None:
        return None
    raise LookupError(method)


def main():
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            res = handle(msg)
            reply = None if res is None else {"jsonrpc": "2.0", "id": msg.get("id"), "result": res}
        except Exception as e:
            reply = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32601, "message": str(e)}}
        if reply is not None and msg.get("id") is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
