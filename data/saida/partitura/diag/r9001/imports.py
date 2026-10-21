"""9001: o que a partitura importa de fora (por arquivo) e os imports relativos."""
import ast, glob, collections, os
cross = collections.defaultdict(set); rel = 0; relfiles = set(); quem_importa = collections.defaultdict(set)
arqs = sorted(glob.glob("tab/partitura_*.py")) + sorted(glob.glob("tests/test_partitura_*.py"))
for f in arqs:
    t = ast.parse(open(f).read())
    for n in ast.walk(t):
        if isinstance(n, ast.ImportFrom):
            if n.level > 0:
                rel += 1; relfiles.add(f)
            m = n.module or ""
            if m.startswith("tab."):
                m = m[4:]
            elif n.level == 0:
                if m == "tab":
                    for a in n.names:
                        if not a.name.startswith("partitura_"):
                            cross[a.name].add((os.path.basename(f), "<mod>"))
                continue
            if m.startswith("partitura_"):
                continue
            for a in n.names:
                cross[m].add((os.path.basename(f), a.name))
print("imports relativos:", rel, "linhas em", len(relfiles), "arquivos")
for m, s in sorted(cross.items()):
    arqs_m = sorted({x[0] for x in s}); nomes = sorted({x[1] for x in s})
    print(f"{m}: {len(arqs_m)} arquivos {nomes} <- {arqs_m}")
# quem fora da partitura importa a partitura
for f in sorted(glob.glob("tab/*.py") + glob.glob("tests/*.py")):
    if "partitura" in os.path.basename(f):
        continue
    src = open(f).read()
    if "partitura_" in src:
        t = ast.parse(src)
        for n in ast.walk(t):
            if isinstance(n, ast.ImportFrom) and n.module and "partitura_" in n.module:
                print("FORA importa partitura:", f, n.module)
