import numpy as np
from PIL import Image
def embed(src):
    """Colour-histogram + 8x8 layout vector. Swap for CLIP later; interface stays the same."""
    im = Image.open(src).convert("RGB").resize((64, 64)); a = np.asarray(im)
    h = np.concatenate([np.histogram(a[..., c], bins=8, range=(0, 255))[0] for c in range(3)]).astype(float)
    g = np.asarray(im.convert("L").resize((8, 8))).flatten().astype(float)
    v = np.concatenate([h / h.sum(), g / (np.linalg.norm(g) or 1)]); return (v / np.linalg.norm(v)).tolist()
def similar(vec, products, n=8):
    q = np.array(vec); s = [(float(q @ np.array(p.embedding)), p) for p in products if p.embedding]
    return [p for _, p in sorted(s, key=lambda x: -x[0])[:n]]
