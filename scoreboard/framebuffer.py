"""Push finished images to the screen's framebuffer."""
import glob
import os

import config


class Framebuffer:
    def __init__(self, path=config.FRAMEBUFFER):
        self.path = self._find() if path == "auto" else path
        name = os.path.basename(self.path)
        sysfs = f"/sys/class/graphics/{name}"
        try:
            with open(f"{sysfs}/virtual_size") as f:
                self.w, self.h = (int(v) for v in f.read().strip().split(","))
            with open(f"{sysfs}/bits_per_pixel") as f:
                self.bpp = int(f.read().strip())
        except OSError:
            self.w, self.h, self.bpp = config.WIDTH, config.HEIGHT, 16
        print(f"Using {self.path}: {self.w}x{self.h}, {self.bpp}-bit")

    @staticmethod
    def _find():
        # Prefer the framebuffer whose driver name looks like a small SPI screen
        for p in sorted(glob.glob("/sys/class/graphics/fb*")):
            try:
                with open(f"{p}/name") as f:
                    n = f.read().lower()
            except OSError:
                continue
            if any(k in n for k in ("ili9", "hx83", "st77", "pitft", "fb_")):
                return "/dev/" + os.path.basename(p)
        return "/dev/fb1" if os.path.exists("/dev/fb1") else "/dev/fb0"

    def show(self, img):
        if config.FLIP:
            img = img.rotate(config.FLIP)
        if (img.width, img.height) != (self.w, self.h):
            if (img.height, img.width) == (self.w, self.h):
                img = img.rotate(90, expand=True)
            else:
                img = img.resize((self.w, self.h))
        with open(self.path, "wb") as f:
            f.write(_to_bytes(img, self.bpp))


def _to_bytes(img, bpp):
    img = img.convert("RGB")
    if bpp == 32:
        return img.convert("RGBA").tobytes("raw", "BGRA")
    try:
        import numpy as np
        a = np.asarray(img, dtype=np.uint16)
        v = ((a[:, :, 0] >> 3) << 11) | ((a[:, :, 1] >> 2) << 5) | (a[:, :, 2] >> 3)
        return v.astype("<u2").tobytes()
    except ImportError:  # slow pure-Python fallback
        out = bytearray()
        for r, g, b in img.getdata():
            v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
            out += bytes((v & 0xFF, v >> 8))
        return bytes(out)
