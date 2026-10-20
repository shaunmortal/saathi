"""Writes textures/floor_tiles.jpg: 4x4 vitrified tiles (60 cm each in the world) with grout and slight shade variation."""
import numpy as np, cv2, pathlib
rng = np.random.default_rng(3)
N, T = 1024, 256
img = np.zeros((N, N, 3), np.float32)
for i in range(4):
    for j in range(4):
        base = np.array([0.86, 0.87, 0.86]) + rng.normal(0, 0.012)
        noise = cv2.GaussianBlur(rng.normal(0, 0.02, (T, T)).astype(np.float32), (0, 0), 6)[..., None]
        img[i*T:(i+1)*T, j*T:(j+1)*T] = base + noise
g = 3  # grout half-width in px
for k in range(0, N + 1, T):
    img[max(0, k-g):k+g, :] = (0.62, 0.62, 0.60)
    img[:, max(0, k-g):k+g] = (0.62, 0.62, 0.60)
out = pathlib.Path(__file__).resolve().parents[1] / "textures" / "floor_tiles.jpg"
cv2.imwrite(str(out), np.clip(img[..., ::-1] * 255, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 90])
print(out)
