"""In-place web UI fixes (brain/ui/brand/compact_summary.py): python3 brain/test_ui_patches.py (stdlib; node optional)"""
import os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "ui", "brand"))
import compact_summary  # noqa: E402

# the upstream shape (dist-server JS of claudecodeui 1.37.5): the normaliser draws a flagged string as the summary
JS = """function isInternalContent(content) {
    return false;
}
export class ClaudeSessionsProvider {
    normalizeMessageRows(raw, sessionId) {
        const c = raw.message.content;
        if (raw.isCompactSummary === true && typeof c === 'string') return [{ role: 'assistant', isCompactSummary: true, content: c }];
        return [{ role: 'user', content: Array.isArray(c) ? c.map((p) => p.text).join('') : c }];
    }
    normalizeMessage(rawMessage, sessionId) {
        const messages = this.normalizeMessageRows(rawMessage, sessionId);
        return messages;
    }
}
"""
TS = JS.replace("normalizeMessage(rawMessage, sessionId) {", "normalizeMessage(rawMessage: unknown, sessionId: string | null): NormalizedMessage[] {")

tmp = tempfile.mkdtemp()
js, ts = os.path.join(tmp, "p.mjs"), os.path.join(tmp, "p.ts")
open(js, "w").write(JS)
open(ts, "w").write(TS)
assert compact_summary.patch(js) and not compact_summary.patch(js), "patched once, then left alone"
assert compact_summary.patch(ts, ts=True)
t = open(ts).read()
assert "function paasCompactSummary(raw: any): any {" in t and "rawMessage = paasCompactSummary(rawMessage);" in t
open(os.path.join(tmp, "bad.js"), "w").write("export class X {}\n")
r = subprocess.run([sys.executable, os.path.join(HERE, "ui", "brand", "compact_summary.py"), os.path.join(tmp, "bad.js")], capture_output=True, text=True)
assert r.returncode == 1 and "upstream text not found" in r.stderr, r
print("patch ok")

node = shutil.which("node")
if node:
    test = os.path.join(tmp, "t.mjs")
    open(test, "w").write("""import { ClaudeSessionsProvider as C } from './p.mjs';
const p = new C(), row = (content, extra) => ({ type: 'user', ...extra, message: { role: 'user', content } });
const pre = 'This session is being continued from a previous conversation that ran out of context.';
const out = [row([{ type: 'text', text: pre }]), row([{ type: 'text', text: 'S' }], { isCompactSummary: true }), row(pre),
             row([{ type: 'text', text: 'hello' }]), row([{ type: 'text', text: pre }], { isMeta: true })]
  .map((r) => p.normalizeMessage(r, 's')[0].role);
console.log(out.join(','));
""")
    o = subprocess.run([node, test], capture_output=True, text=True)
    assert o.stdout.strip() == "assistant,assistant,assistant,user,user", o.stdout + o.stderr
    print("summary rows drawn as the summary, the user's own text as theirs: ok")
print("ui patches ok")
