"""Composicao: alpha sobre base float."""
import numpy as np


def sobre(base, lay, x=0, y=0):
    """Cola `lay` (h,w,4) em `base` (H,W,3) com o canto em (x,y); recorta nas bordas."""
    H, W = base.shape[:2]; h, w = lay.shape[:2]
    x, y = int(round(x)), int(round(y))
    xa, ya = max(0, x), max(0, y); xb, yb = min(W, x + w), min(H, y + h)
    if xa >= xb or ya >= yb:
        return base
    l = lay[ya - y:yb - y, xa - x:xb - x]
    a = l[..., 3:4]
    if a.max() > 1.5:                 # asset do disco: alfa em 0-255
        a = a / 255.0
    base[ya:yb, xa:xb] = base[ya:yb, xa:xb] * (1 - a) + l[..., :3] * a
    return base
