"""Offline test of sync_dell.py: fake Dell hub pages and PDFs, no network."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync"))
import sync_dell  # noqa: E402

HUB = """<html><body>
<a href="https://dl.dell.com/content/docu88904_PowerMax_Family_Product_Guide.pdf?language=en_US&amp;source=Coveo">PowerMax Family <b>Product Guide</b></a>
<a href="https://www.dell.com/en-sg/collaterals/unauth/white-papers/products/storage/h8115-vmware-vstorage-vmax-wp.pdf">Using VAAI with VMAX and PowerMax</a>
<a href="https://dl.dell.com/content/manual47140932-dell-powerflex-5-1-x-technical-overview.pdf">PowerFlex 5.1 Technical Overview</a>
<a href="https://dl.dell.com/content/docu88904_PowerMax_Family_Product_Guide.pdf?language=en_US">duplicate link</a>
<a href="https://evil.example.com/malware.pdf">not Dell</a>
<a href="https://dl.dell.com/content/login.pdf">login page instead of pdf</a>
</body></html>"""
CALLS = []


def fake_fetch(url, timeout=120):
    CALLS.append(url)
    if url.endswith(".htm") or "kbdoc" in url:
        return HUB.encode() if url.endswith(".htm") else b"<html><title>KB 000204833</title><p>naa decode</p></html>", "text/html"
    if "login.pdf" in url:
        return b"<html>please sign in</html>", "text/html"
    return b"%PDF-1.4 fake pdf " + url.encode(), "application/pdf"


sync_dell.fetch = fake_fetch
d = tempfile.mkdtemp()
src = os.path.join(d, "src.txt")
open(src, "w").write("# test\nhub powermax https://www.dell.com/en-sg/dt/documentation/vmax-all-flash-family.htm\n"
                     "page powermax https://www.dell.com/support/kbdoc/en-us/000204833/how-to-know-naa\n"
                     "bad line here\n")
sys.argv = ["x", "--dest", os.path.join(d, "dell"), "--sources", src, "--delay", "0"]
sync_dell.main()
files = sorted(os.listdir(os.path.join(d, "dell", "powermax")))
print(files)
m = json.load(open(os.path.join(d, "dell", "powermax", "manifest.json")))
assert "docu88904_PowerMax_Family_Product_Guide.pdf" in files and "h8115-vmware-vstorage-vmax-wp.pdf" in files
assert "manual47140932-dell-powerflex-5-1-x-technical-overview.pdf" in files
assert not any("malware" in f or f == "login.pdf" for f in files), files
assert m["docu88904_PowerMax_Family_Product_Guide.pdf"]["title"] == "PowerMax Family Product Guide"
assert sum("docu88904" in c for c in CALLS) == 1, "duplicate downloaded"
assert not any("evil.example.com" in c for c in CALLS)
n = len(CALLS)
sync_dell.main()  # second run: nothing new except the hub page
assert CALLS[n:] == ["https://www.dell.com/en-sg/dt/documentation/vmax-all-flash-family.htm", "https://dl.dell.com/content/login.pdf"], CALLS[n:]  # hub + retry of the failed one only
print("ALL TESTS PASSED")
