#!/usr/bin/env python3
"""Refuse a broken site. Exits non-zero on any failure.

This exists because on 15 Sep 2026 the same checks were run as a throwaway
snippet that printed its failures and exited 0 - so a page with a 164-character
meta description was committed and pushed while the output said FAILURES: 1.
A check that cannot fail the build is a note, not a gate.

    python3 CHECK-SITE.py
"""
import os, re, json, glob, sys

BASE = "https://bluetigre.com"
NDA_TERMS = ("diol", "polyester plasticizer", "bdo",   # the engagement under NDA
             "refrigerat")                            # a client's own product line
PUBLIC_EMAIL, WORK_EMAIL = "info@bluetigre.com", "jim@bluetigre.com"

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)
    pages = sorted(glob.glob("**/index.html", recursive=True)) + ["404.html"]
    fail, titles, descs = [], {}, {}

    for f in pages:
        h = open(f).read()
        pg = "" if f == "index.html" else f.replace("index.html", "")

        for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
            try: json.loads(m)
            except Exception as e: fail.append(f"{f}: JSON-LD does not parse: {e}")

        got = {}
        for name, pat in (("title", r'<title>(.*?)</title>'),
                          ("description", r'<meta name="description" content="([^"]*)"'),
                          ("canonical", r'<link rel="canonical" href="([^"]+)"')):
            v = re.findall(pat, h)
            if len(v) != 1:
                fail.append(f"{f}: expected exactly one {name}, found {len(v)}")
            got[name] = v[0] if v else ""

        if f != "404.html" and got["canonical"] != f"{BASE}/{pg}":
            fail.append(f"{f}: canonical is {got['canonical']}, expected {BASE}/{pg}")
        if len(got["description"]) > 160:
            fail.append(f"{f}: description is {len(got['description'])} chars, max 160")
        for name, seen in (("title", titles), ("description", descs)):
            v = got[name]
            if v in seen: fail.append(f"{f}: duplicate {name}, same as {seen[v]}")
            seen[v] = f

        for img in re.findall(r'<img[^>]*>', h):
            alt = re.findall(r'alt="([^"]*)"', img)
            if not alt or not alt[0].strip():
                fail.append(f"{f}: image with empty or missing alt text")

        base_dir = os.path.dirname(f)
        for href in re.findall(r'href="([^"]+)"', h):
            if href.startswith(("http", "mailto:", "#")): continue
            t = os.path.normpath(os.path.join(base_dir, href))
            if not any(os.path.exists(x) for x in (t, os.path.join(t, "index.html"))):
                fail.append(f"{f}: broken internal link -> {href}")

        # info@ is the published address (decided 28 Aug 2026, reaffirmed 15 Sep).
        if WORK_EMAIL in h: fail.append(f"{f}: carries the work address on a public page")
        if PUBLIC_EMAIL not in h: fail.append(f"{f}: missing the public address")

        for term in NDA_TERMS:
            if term in h.lower():
                fail.append(f"{f}: NDA term '{term}' - that engagement may not be published")

    for extra in ("llms.txt",):
        h = open(extra).read()
        if WORK_EMAIL in h: fail.append(f"{extra}: carries the work address")
        for term in NDA_TERMS:
            if term in h.lower(): fail.append(f"{extra}: NDA term '{term}'")

    locs = {l.replace(BASE + "/", "") for l in
            re.findall(r'<loc>([^<]+)</loc>', open("sitemap.xml").read())}
    disk = {("" if f == "index.html" else f.replace("index.html", ""))
            for f in pages if f != "404.html"}
    if locs != disk:
        fail.append(f"sitemap disagrees with the pages on disk: {sorted(locs ^ disk)}")

    print(f"{len(pages)} pages, {len(locs)} sitemap urls")
    if fail:
        print(f"\nREFUSED - {len(fail)} failure(s):")
        for x in fail: print("  -", x)
        return 1
    print("SITE AGREES WITH ITS OWN RULES")
    return 0

if __name__ == "__main__":
    sys.exit(main())
