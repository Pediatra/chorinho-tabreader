"""Depuração (rodada 0151): dx e resposta por par no trecho 183 a 186 s do kenneth."""

import cv2

from tab import leitor
from tab import rolagem_deslocamento as rd
from tab import rolagem_saltos as rs

V = "/acervo/kenneth acoustic/location - khalid ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4"
qs = list(leitor.quadros(V, 183.0, 186.0, 10.0, recorte_y=(855, 1085)))
print("quadros", len(qs), "shape", qs[0][1].shape)
x1 = 1640
h, w = qs[0][1][:, :x1].shape[:2]
jan = cv2.createHanningWindow((w, h), cv2.CV_32F)
for (ta, qa), (tb, qb) in zip(qs, qs[1:]):
    m = rs.mascara(qa) | rs.mascara(qb)
    ca = rs.cinza_mascarado(qa, 0, x1, m)
    cb = rs.cinza_mascarado(qb, 0, x1, m)
    dx, dy, r = rd.deslocar(ca, cb, jan)
    na = len(rs.barras(ca))
    nb = len(rs.barras(cb))
    print(f"{ta:7.2f}->{tb:7.2f} dx={dx:9.2f} resp={r:.3f} rot={rs.classificar(dx, r)} barras {na}/{nb}")
