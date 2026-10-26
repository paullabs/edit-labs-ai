"""Separa uma gravura anatômica vista de cima em duas camadas que giram independentes: o cérebro (miolo de giros)
e o crânio (anel de osso, dura, couro cabeludo e orelhas, tingidos de osso). Feito para a prancha do crânio aberto de
W. H. Lizars (c. 1826, Wellcome Collection V0008410, CC BY 4.0: crédito obrigatório e mudança declarada).

    clpy separar_lizars.py <prancha.jpg> <pasta_saida>
        -> cerebro_cima.png, cranio_inteiro.png, cranio_anel.png e _mascara_prova.jpg (confira antes de usar)

Os números (região do papel, elipse do cérebro, cortes em y, letras a apagar, linha da nuca) foram medidos nessa
prancha. Para outra gravura, meça os seus e troque. O método vale para qualquer gravura pontilhada: o pontilhado
impede separar por limiar, então o cérebro sai por GrabCut a partir de uma elipse, e a nuca, que a prancha corta
reta, é refeita espelhando a frente (o crânio visto de cima é quase simétrico)."""
import sys
from pathlib import Path

import cv2
import numpy as np

if len(sys.argv) != 3:
    sys.exit(__doc__)
ent, sai = sys.argv[1], Path(sys.argv[2])
sai.mkdir(parents=True, exist_ok=True)
im = cv2.imread(ent)                       # BGR
H, W = im.shape[:2]
lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(np.float32)
papel = np.median(np.concatenate([lab[1200:2000, 120:260].reshape(-1, 3), lab[1200:2000, 1990:2130].reshape(-1, 3)]), axis=0)
dist = np.linalg.norm(cv2.GaussianBlur(lab, (0, 0), 6) - papel, axis=2)   # o papel tem pontilhado: compara borrado

# cabeça inteira: tudo o que se afasta do papel, sem buracos, maior componente
cab = (dist > 20).astype(np.uint8)
cab = cv2.morphologyEx(cab, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
n, lb, st, _ = cv2.connectedComponentsWithStats(cab)
k = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])
cab = (lb == k).astype(np.uint8)
cnt, _ = cv2.findContours(cab, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cab = np.zeros_like(cab); cv2.drawContours(cab, cnt, -1, 1, -1)
# corta a foice (o "D") que pende embaixo, abaixo do fim do crânio
cab[2330:, :] = 0

# cérebro: GrabCut a partir de uma elipse (centro e semieixos medidos na prancha); o pontilhado da gravura impede
# separar por limiar de escuro
CX, CY, AX, AY = 1110, 1570, 610, 740
mk = np.full((H, W), cv2.GC_BGD, np.uint8)
cv2.ellipse(mk, (CX, CY), (AX + 90, AY + 90), 0, 0, 360, cv2.GC_PR_BGD, -1)
cv2.ellipse(mk, (CX, CY), (AX + 25, AY + 25), 0, 0, 360, cv2.GC_PR_FGD, -1)
cv2.ellipse(mk, (CX, CY), (AX - 110, AY - 120), 0, 0, 360, cv2.GC_FGD, -1)
mk[cab == 0] = cv2.GC_BGD
f = 0.5
pq = cv2.resize(cv2.GaussianBlur(im, (0, 0), 2), None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
mq = cv2.resize(mk, (pq.shape[1], pq.shape[0]), interpolation=cv2.INTER_NEAREST)
bg, fg = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
cv2.grabCut(pq, mq, None, bg, fg, 6, cv2.GC_INIT_WITH_MASK)
cer = cv2.resize(((mq == cv2.GC_FGD) | (mq == cv2.GC_PR_FGD)).astype(np.uint8), (W, H), interpolation=cv2.INTER_LINEAR)
cer = cv2.morphologyEx(cer, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
n, lb, st, _ = cv2.connectedComponentsWithStats(cer)
k = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])
cer = (lb == k).astype(np.uint8)
cnt, _ = cv2.findContours(cer, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cer = np.zeros_like(cer); cv2.drawContours(cer, cnt, -1, 1, -1)

# franja: perto da borda (até 70 px), o pontilhado escuro é a fenda/dura, não giro → sai da máscara
dist_borda = cv2.distanceTransform(cer, cv2.DIST_L2, 5)
Lb = cv2.GaussianBlur(lab[..., 0] * 100 / 255, (0, 0), 4)
franja = (dist_borda < 70) & (Lb < 58)
cer = (cer & ~franja).astype(np.uint8)
cer = cv2.morphologyEx(cer, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
cer = cv2.morphologyEx(cer, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
n, lb, st, _ = cv2.connectedComponentsWithStats(cer)
cer = (lb == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)

# retoque: as manchas vermelhas (sangue) e as letras "A" saem por inpaint
hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
verm = (((hsv[..., 0] < 10) | (hsv[..., 0] > 165)) & (hsv[..., 1] > 70)).astype(np.uint8)
verm = cv2.dilate(verm * cer, np.ones((9, 9), np.uint8))
letras = np.zeros((H, W), np.uint8)
for x, y in [(850, 1540), (1290, 1540)]:
    cv2.rectangle(letras, (x - 22, y - 26), (x + 22, y + 22), 1, -1)
limpo = cv2.inpaint(im, ((verm | letras) > 0).astype(np.uint8), 9, cv2.INPAINT_TELEA)

def salvar(nome, bgr, mask, pena=1.2):
    a = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), pena)
    ys, xs = np.where(mask > 0)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgba = np.dstack([bgr, (np.clip(a, 0, 1) * 255).astype(np.uint8)])[y0:y1, x0:x1]
    cv2.imwrite(str(sai / nome), rgba)
    return (x0, y0, x1, y1)

bc = salvar("cerebro_cima.png", limpo, cer)
# crânio: o anel (cabeça menos cérebro), tingido de osso: sem o vermelho do couro, mantém a gravura
cab[2262:, :] = 0                                   # a foice sai; a nuca é refeita por espelho, mais abaixo
anel = (cab & (1 - cv2.dilate(cer, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (91, 91))))).astype(np.uint8)   # o oco vai até o osso: a fenda e a dura viram folga escura
g = cv2.cvtColor(limpo, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
escuro_osso, claro_osso = np.array([52, 58, 70], np.float32), np.array([200, 222, 233], np.float32)  # BGR sépia → creme
osso = (escuro_osso + g[..., None] ** 0.9 * (claro_osso - escuro_osso)).astype(np.uint8)
bk = salvar("cranio_inteiro.png", osso, cab)            # o crânio guarda o miolo também (fundo escuro por baixo do cérebro)
# nuca: o crânio visto de cima é quase simétrico frente/trás; a parte de trás (y > 1880, onde estavam a foice e o
# corte reto) é refeita com a frente espelhada em torno de y = 1520, alargada para casar com a largura na emenda
Y0, Y1, EIXO, CX = 1880, 1990, 1520, 1098
FIM = 2 * EIXO - 735
def largura(m, y):
    xs = np.where(m[y] > 0)[0]
    return (xs.max() - xs.min()) if len(xs) else 1
sx = largura(anel, Y0) / largura(anel, 2 * EIXO - Y0)
gx = np.arange(W, dtype=np.float32)
mapx = (CX + (gx - CX) / sx).astype(np.float32)
pad = FIM + 4 - H
if pad > 0:
    anel = np.pad(anel, ((0, pad), (0, 0))); osso = np.pad(osso, ((0, pad), (0, 0), (0, 0)))
    cab = np.pad(cab, ((0, pad), (0, 0))); H2 = H + pad
am = anel.astype(np.float32)
om = osso.astype(np.float32)
for y in range(Y0, FIM):
    src = 2 * EIXO - y
    linha_a = cv2.remap(anel[src:src + 1].astype(np.float32), mapx[None, :], np.zeros((1, W), np.float32), cv2.INTER_LINEAR)[0]
    linha_o = cv2.remap(osso[src:src + 1].astype(np.float32), mapx[None, :], np.zeros((1, W), np.float32), cv2.INTER_LINEAR)[0]
    w = min(1.0, max(0.0, (y - Y0) / (Y1 - Y0)))
    am[y] = (1 - w) * am[y] + w * linha_a
    om[y] = (1 - w) * om[y] + w * linha_o
anel = (am > 0.5).astype(np.uint8)
osso = np.clip(om, 0, 255).astype(np.uint8)
ba = salvar("cranio_anel.png", osso, anel)
print("cérebro", bc, "crânio", bk, "anel", ba)
cv2.imwrite(str(sai / "_mascara_prova.jpg"), cv2.resize(np.dstack([cab * 120, cer * 255, anel * 200]).astype(np.uint8), (W // 4, H // 4)))
