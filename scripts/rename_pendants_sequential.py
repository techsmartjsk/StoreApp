#!/usr/bin/env python3
"""One-time migration: rename pendant images into sequential, probe-able codes.

Old (arbitrary codes, needs a generated map):
    pendant_{metal}_{gem}_{ARBITRARY}.{ext}   e.g. pendant_copper_blue-sapphire_BS01.JPG

New (sequential per metal+gem, discoverable by CDN probing, no map):
    pendant_{metal}_{gem}_{PREFIX}{NN}.{ext}  e.g. pendant_copper_blue-sapphire_CO01.jpg

- gem token is normalised to its handleized form (lowercase, spaces -> hyphens)
  so it matches `product.metafields.custom.gem_type | handleize` used in Liquid.
- extension is lowercased (Shopify CDN is case-sensitive; JS probes lowercase).
- numbering is contiguous starting at 01 so the browser can stop probing at the
  first gap.

Run with --apply to actually `git mv`; without it, prints the plan only.
"""
import os, re, subprocess, sys
from collections import defaultdict

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
PREFIX = {"copper": "CO", "gold": "GL", "silver": "SL",
          "platinum": "PL", "white-gold": "WG", "panchdhatu": "PN"}

# pendant_{metal}_{gem}_{code}.{ext}  (gem may contain spaces/hyphens/mixed case)
PAT = re.compile(r"^pendant_([a-z]+)_(.+)_([A-Za-z0-9]+)\.([A-Za-z]+)$")

def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

def main(apply):
    groups = defaultdict(list)            # (metal, gem) -> [filename, ...]
    skipped = []
    for f in os.listdir(ASSETS):
        if not f.startswith("pendant_") or f.endswith((".svg", ".js")):
            continue
        m = PAT.match(f)
        if not m:
            skipped.append(f); continue
        metal, gem_raw, _code, ext = m.groups()
        if metal not in PREFIX:
            skipped.append(f); continue
        gem = gem_raw.replace(" ", "-").lower()       # handleize-equivalent
        groups[(metal, gem)].append((f, ext.lower()))

    plan = []                              # (old, new)
    for (metal, gem), files in sorted(groups.items()):
        files.sort(key=lambda t: natural_key(t[0]))
        for i, (old, ext) in enumerate(files, start=1):
            new = f"pendant_{metal}_{gem}_{PREFIX[metal]}{i:02d}.{ext}"
            if new != old:
                plan.append((old, new))

    # guard: never overwrite an existing different file
    existing = set(os.listdir(ASSETS))
    targets = {n for _, n in plan}
    for _, n in plan:
        if n in existing and n not in {o for o, _ in plan}:
            print(f"!! target already exists, aborting: {n}"); sys.exit(1)
    if len(targets) != len(plan):
        print("!! duplicate target names, aborting"); sys.exit(1)

    for old, new in plan:
        print(f"  {old}\n    -> {new}")
        if apply:
            subprocess.run(["git", "-C", os.path.join(ASSETS, ".."), "mv", "-f",
                            os.path.join("assets", old), os.path.join("assets", new)],
                           check=True)
    print(f"\n{len(plan)} files {'renamed' if apply else 'to rename'}; "
          f"{len(groups)} metal+gem groups; {len(skipped)} skipped.")
    if skipped:
        print("Skipped (unparsed):")
        for s in sorted(skipped): print("  " + s)

if __name__ == "__main__":
    main("--apply" in sys.argv)
