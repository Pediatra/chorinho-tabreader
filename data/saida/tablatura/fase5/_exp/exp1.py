import sys
sys.path.insert(0, "/app")
from tab import leitor
from tab.cursor import detectar_cursor
V = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
for t0, t1, y0, y1 in [(239.4, 265.9, 297, 446)]:
    for t, q in leitor.quadros(V, t0, t1, 6.0, recorte_y=(y0, y1)):
        d = detectar_cursor(q)
        print(f"{t:8.2f}", None if d is None else (d[0], d[1], d[2]))
