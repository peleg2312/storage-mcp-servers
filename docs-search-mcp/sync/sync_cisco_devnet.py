#!/usr/bin/env python3
"""Cisco DevNet API documentation (developer.cisco.com, public, plain HTTP) -> work/docs/cisco/<product>/<doc>/.

Each DevNet doc keeps its table of contents in https://pubhub.devnetcloud.com/media/<doc>/docs/config.json; its items
point to Markdown pages (saved as is) or OpenAPI specs (type swagger / swagger3: rendered to one Markdown page per
tag, every operation with method, path, description, parameters, request body and responses). Links to other sites
are skipped. Resumable: pages already saved are not fetched again.

    python3 sync/sync_cisco_devnet.py [--dest work/docs] [--list sources/cisco-devnet.txt]
"""
import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = "https://pubhub.devnetcloud.com/media/{doc}/docs/"
UA = {"User-Agent": "Mozilla/5.0 (storage-mcp-servers docs sync)"}


def get(url, tries=3):
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code < 500 or n == tries - 1:
                raise
        except OSError:
            if n == tries - 1:
                raise
        time.sleep(5 * (n + 1))


def walk(items, path=()):
    for it in items or []:
        t = it.get("title", "")
        yield path + (t,), it
        yield from walk(it.get("items"), path + (t,))


def ref_name(s):
    return (s or {}).get("$ref", "").rsplit("/", 1)[-1] if isinstance(s, dict) else ""


def schema_txt(s):
    if not isinstance(s, dict):
        return ""
    if "$ref" in s:
        return ref_name(s)
    if s.get("type") == "array":
        return f"array of {schema_txt(s.get('items'))}"
    props = s.get("properties")
    if props:
        return "object {" + ", ".join(f"{k}: {v.get('type', ref_name(v)) if isinstance(v, dict) else v}"
                                      for k, v in list(props.items())[:25]) + "}"
    return s.get("type", "")


def render_openapi(spec, title):
    """{tag: markdown} - one page per tag with every operation."""
    pages = {}
    for path, ops in (spec.get("paths") or {}).items():
        for method, op in ops.items():
            if method.lower() not in ("get", "post", "put", "patch", "delete") or not isinstance(op, dict):
                continue
            tag = (op.get("tags") or ["other"])[0]
            md = [f"## {method.upper()} {path}", ""]
            if op.get("summary"):
                md.append(op["summary"].strip())
            if op.get("description") and op.get("description") != op.get("summary"):
                md.append(re.sub(r"\s+", " ", op["description"]).strip())
            params = op.get("parameters") or []
            if params:
                md += ["", "| Parameter | In | Required | Type | Description |", "|---|---|---|---|---|"]
                for p in params:
                    if "$ref" in p:
                        md.append(f"| {ref_name(p)} | | | | |")
                        continue
                    md.append(f"| {p.get('name')} | {p.get('in')} | {p.get('required', False)} | "
                              f"{schema_txt(p.get('schema')) or p.get('type', '')} | "
                              f"{re.sub(r'\s+', ' ', p.get('description', '')).replace('|', '/')[:200]} |")
            body = (op.get("requestBody") or {}).get("content", {})
            for ctype, c in body.items():
                md.append(f"\nRequest body ({ctype}): {schema_txt(c.get('schema'))}")
            resp = op.get("responses") or {}
            if resp:
                md.append("\nResponses: " + "; ".join(f"{code} {re.sub(r'\s+', ' ', (r or {}).get('description', ''))[:120]}"
                                                       for code, r in resp.items()))
            pages.setdefault(tag, [f"# {title}: {tag}", ""]).extend(md + [""])
    schemas = (spec.get("components") or {}).get("schemas") or spec.get("definitions") or {}
    if schemas:
        md = [f"# {title}: data models", ""]
        for name, s in schemas.items():
            md += [f"## {name}", schema_txt(s), ""]
        pages["data models"] = md
    return {t: "\n".join(v) + "\n" for t, v in pages.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="work/docs")
    ap.add_argument("--list", default=os.path.join(HERE, "sources", "cisco-devnet.txt"))
    ap.add_argument("--delay", type=float, default=0.5)
    a = ap.parse_args()
    for line in open(a.list, encoding="utf-8"):
        p = line.split("#", 1)[0].split()
        if len(p) < 3:
            continue
        product, doc, site = p[0], p[1], p[2]
        d = os.path.join(a.dest, "cisco", product, doc)
        os.makedirs(d, exist_ok=True)
        mf = os.path.join(d, "manifest.json")
        man = json.load(open(mf)) if os.path.exists(mf) else {}
        base = MEDIA.format(doc=doc)
        try:
            conf = json.loads(get(base + "config.json"))
        except Exception as e:
            print(f"{doc}: no config.json ({e})")
            continue
        new, specs = 0, set()
        top = next((t for t in (it.get("title") for it in conf.get("items", [])) if t), doc)
        for path, it in walk(conf.get("items")):
            kind, content = it.get("type", ""), it.get("content", "")
            if not content or kind in ("url", "config") or content.startswith("http"):
                continue
            title = f"{path[-1]} - {top}" if path[-1] != top else top       # the page's own name first
            if kind in ("swagger", "swagger2", "swagger3", "openapi") or content.endswith((".json", ".yaml", ".yml")):
                if not content.endswith(".json") or content in specs:      # one spec can be linked twice
                    continue
                specs.add(content)
                try:
                    spec = json.loads(get(base + urllib.parse.quote(content)))
                except Exception as e:
                    print(f"{doc}: spec failed {content}: {e}")
                    continue
                label = re.sub(r"^Download\s+'?(\w+)'?\s+Spec$", r"API Reference (\1)", path[-1] or doc)
                for tag, md in render_openapi(spec, label).items():
                    name = re.sub(r"[^\w.-]+", "-", f"{os.path.splitext(os.path.basename(content))[0]}--{tag}")[:150] + ".md"
                    open(os.path.join(d, name), "w", encoding="utf-8").write(md)
                    man[name] = {"url": site, "title": f"{label}: {tag}"}
                    new += 1
                continue
            if not content.endswith(".md"):
                continue
            name = re.sub(r"[^\w.-]+", "-", content)[:150]
            if name in man:
                continue
            try:
                md = get(base + urllib.parse.quote(content)).decode("utf-8", "replace")
            except Exception as e:
                print(f"{doc}: failed {content}: {e}")
                continue
            if not md.lstrip().startswith("#"):
                md = f"# {path[-1]}\n\n{md}"
            open(os.path.join(d, name), "w", encoding="utf-8").write(md)
            man[name] = {"url": site, "title": title}
            new += 1
            time.sleep(a.delay)
        json.dump(man, open(mf, "w"), indent=1)
        print(f"{product}/{doc}: {new} new, {len(man)} pages -> {d}")


if __name__ == "__main__":
    main()
