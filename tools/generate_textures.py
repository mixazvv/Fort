#!/usr/bin/env python3
"""Процедурные текстуры для карты «Склад 17» (BODYCAM для Fortnite/UEFN).

Генерирует бесшовные PBR-наборы (BaseColor, Normal в формате DirectX/Unreal,
Roughness) и декали с альфа-каналом. Нужны только numpy и Pillow.

    python3 tools/generate_textures.py               # 1024 px в textures/
    python3 tools/generate_textures.py --size 2048   # 2K
"""

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


# ---------------------------------------------------------------- шум

def value_noise(size, cells_x, cells_y, rng):
    """Бесшовный value noise: сетка случайных значений со сглаженной интерполяцией и заворотом краёв."""
    grid = rng.random((cells_y, cells_x))
    xs = np.arange(size) * cells_x / size
    ys = np.arange(size) * cells_y / size
    x0 = np.floor(xs).astype(int)
    y0 = np.floor(ys).astype(int)
    tx = xs - x0
    ty = ys - y0
    tx = tx * tx * (3 - 2 * tx)
    ty = ty * ty * (3 - 2 * ty)
    x1 = (x0 + 1) % cells_x
    y1 = (y0 + 1) % cells_y
    a = grid[np.ix_(y0, x0)]
    b = grid[np.ix_(y0, x1)]
    c = grid[np.ix_(y1, x0)]
    d = grid[np.ix_(y1, x1)]
    top = a + (b - a) * tx[None, :]
    bottom = c + (d - c) * tx[None, :]
    return top + (bottom - top) * ty[:, None]


def fbm(size, cells, rng, octaves=5, persistence=0.5, stretch=(1, 1)):
    """Фрактальный шум 0..1. stretch растягивает клетки (для волокон дерева, подтёков)."""
    total = np.zeros((size, size))
    amplitude, norm = 1.0, 0.0
    for octave in range(octaves):
        c = cells * 2 ** octave
        cx = max(1, min(size, int(c * stretch[0])))
        cy = max(1, min(size, int(c * stretch[1])))
        total += value_noise(size, cx, cy, rng) * amplitude
        norm += amplitude
        amplitude *= persistence
    return total / norm


def blur(a, radius=1):
    """Размытие с заворотом краёв, чтобы не ломать бесшовность."""
    out = np.zeros_like(a)
    count = 0
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            out += np.roll(np.roll(a, dy, axis=0), dx, axis=1)
            count += 1
    return out / count


def contrast(x, low, high):
    return np.clip((x - low) / (high - low), 0, 1)


def crack_lines(size, rng, cells=4, width=0.006, coverage=0.55):
    """Тонкие извилистые трещины: изолинии шума, оставленные только местами."""
    field = fbm(size, cells, rng, octaves=6, persistence=0.55)
    lines = np.exp(-((field - 0.5) / width) ** 2)
    mask = contrast(fbm(size, 3, rng, octaves=3), coverage, coverage + 0.15)
    return lines * mask


def grid_coords(size):
    v, u = np.mgrid[0:size, 0:size] / size
    return u, v


def tint(gray, color):
    return gray[..., None] * np.array(color)[None, None, :]


def normal_from_height(height, strength):
    """Карта нормалей в формате DirectX (как в Unreal): зелёный канал смотрит вниз по изображению."""
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * strength
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * strength
    n = np.stack([-dx, -dy, np.ones_like(height)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


# ---------------------------------------------------------------- материалы
# Каждая функция возвращает (albedo RGB 0..1, height 0..1, roughness 0..1, сила нормали).

def concrete_floor(size, rng):
    """Бетонный пол цеха: пятна, поры, трещины, нарезанные швы, следы шин."""
    u, v = grid_coords(size)
    base = 0.40 + 0.10 * (fbm(size, 4, rng) - 0.5) + 0.05 * (fbm(size, 32, rng, octaves=3) - 0.5)
    stains = contrast(fbm(size, 3, rng, octaves=4), 0.55, 0.8)
    oil = contrast(fbm(size, 6, rng, octaves=4), 0.68, 0.82)
    pores = np.clip(blur((rng.random((size, size)) > 0.993).astype(float), 1) * 4, 0, 1)
    cracks = crack_lines(size, rng)
    joint = np.maximum(np.exp(-((u - 0.5) / 0.0025) ** 2), np.exp(-((v - 0.5) / 0.0025) ** 2))
    tires = contrast(fbm(size, 2, rng, octaves=3, stretch=(0.25, 6)), 0.6, 0.85) * 0.5

    gray = base * (1 - 0.25 * stains) * (1 - 0.45 * oil) * (1 - 0.25 * tires)
    gray = gray * (1 - 0.6 * cracks) * (1 - 0.7 * joint) * (1 - 0.4 * pores)
    albedo = tint(gray, (1.0, 0.98, 0.94))
    height = 0.6 + 0.08 * fbm(size, 24, rng, octaves=4) - 0.35 * cracks - 0.4 * joint - 0.2 * pores
    rough = 0.82 - 0.25 * oil - 0.08 * stains + 0.05 * fbm(size, 16, rng)
    return albedo, height, rough, 3.0


def concrete_block_wall(size, rng):
    """Окрашенная стена из шлакоблоков (блок 40×20 см, текстура 2×2 м), сколы краски, грязь."""
    u, v = grid_coords(size)
    rows, cols = 10, 5
    row = np.floor(v * rows)
    shifted = (u * cols + 0.5 * (row % 2)) % 1.0
    fy = (v * rows) % 1.0
    mortar = np.maximum(contrast(0.04 - np.minimum(shifted, 1 - shifted), 0, 0.03),
                        contrast(0.07 - np.minimum(fy, 1 - fy), 0, 0.05))
    block_id = (np.floor(u * cols + 0.5 * (row % 2)) % cols) + row * cols
    block_var = (np.sin(block_id * 12.9898) * 43758.5453) % 1.0

    paint = np.array((0.56, 0.60, 0.55))
    raw = np.array((0.45, 0.44, 0.42))
    chips = contrast(fbm(size, 16, rng, octaves=5), 0.7, 0.73)
    grime = contrast(fbm(size, 3, rng, octaves=4), 0.35, 0.9)
    speckle = fbm(size, 64, rng, octaves=2)

    albedo = paint[None, None, :] * (1 - chips[..., None]) + raw[None, None, :] * chips[..., None]
    albedo = albedo * (0.92 + 0.08 * block_var[..., None]) * (0.95 + 0.1 * speckle[..., None])
    albedo = albedo * (1 - 0.3 * grime[..., None])
    albedo = albedo * (1 - 0.35 * mortar[..., None])
    height = 0.7 - 0.5 * mortar - 0.08 * chips + 0.06 * speckle
    rough = 0.7 + 0.15 * chips + 0.1 * grime
    return albedo, height, rough, 4.0


def corrugated_metal(size, rng):
    """Профлист: вертикальные рёбра, оцинковка, ржавые подтёки, царапины."""
    u, v = grid_coords(size)
    ribs = 8
    profile = 0.5 + 0.5 * np.sin(2 * np.pi * ribs * u)
    profile = np.clip(profile * 1.4 - 0.2, 0, 1)
    streaks = contrast(fbm(size, 4, rng, octaves=5, stretch=(4, 0.25)), 0.55, 0.85)
    rust_spots = contrast(fbm(size, 10, rng, octaves=5), 0.7, 0.82)
    rust = np.clip(streaks * 0.8 + rust_spots, 0, 1)
    scratches = contrast(fbm(size, 4, rng, octaves=3, stretch=(12, 0.1)), 0.82, 0.9) * 0.5

    metal = np.array((0.52, 0.56, 0.58))
    rust_color = np.array((0.38, 0.20, 0.10))
    shade = 0.85 + 0.15 * profile
    albedo = metal[None, None, :] * (1 - rust[..., None]) + rust_color[None, None, :] * rust[..., None]
    albedo = albedo * shade[..., None] * (0.92 + 0.08 * fbm(size, 32, rng, octaves=2))[..., None]
    albedo = np.clip(albedo + 0.12 * scratches[..., None], 0, 1)
    height = 0.2 + 0.7 * profile + 0.05 * rust_spots
    rough = 0.45 + 0.4 * rust - 0.15 * scratches
    return albedo, height, rough, 6.0


def asphalt(size, rng):
    """Асфальт двора: крупный щебень, трещины, заплатки."""
    base = 0.20 + 0.04 * (fbm(size, 6, rng) - 0.5) + 0.04 * (fbm(size, 128, rng, octaves=2) - 0.5)
    aggregate = rng.random((size, size))
    stones = blur(contrast(aggregate, 0.96, 1.0) * 0.12 - contrast(1 - aggregate, 0.97, 1.0) * 0.04, 1) * 2
    patches = contrast(fbm(size, 2, rng, octaves=3), 0.62, 0.64)
    cracks = crack_lines(size, rng, cells=3, width=0.008, coverage=0.5)
    wet = contrast(fbm(size, 3, rng, octaves=4), 0.6, 0.75)

    gray = (base + stones) * (1 - 0.2 * patches) * (1 - 0.7 * cracks) * (1 - 0.12 * wet)
    albedo = tint(np.clip(gray, 0, 1), (1.0, 1.0, 1.02))
    height = 0.5 + 0.4 * stones * 5 - 0.4 * cracks + 0.05 * patches
    rough = 0.9 - 0.55 * wet - 0.05 * patches
    return albedo, np.clip(height, 0, 1), rough, 3.0


def office_floor_tiles(size, rng):
    """Виниловая плитка 30 см в офисах: два цвета, потёртости, швы."""
    u, v = grid_coords(size)
    n = 8
    fx, fy = (u * n) % 1.0, (v * n) % 1.0
    seam = np.maximum(contrast(0.012 - np.minimum(fx, 1 - fx), 0, 0.012),
                      contrast(0.012 - np.minimum(fy, 1 - fy), 0, 0.012))
    checker = (np.floor(u * n) + np.floor(v * n)) % 2
    tile_id = np.floor(u * n) * 17 + np.floor(v * n) * 31
    tile_var = (np.sin(tile_id * 12.9898) * 43758.5453) % 1.0

    light = np.array((0.66, 0.62, 0.53))
    dark = np.array((0.42, 0.45, 0.47))
    albedo = light[None, None, :] * (1 - checker[..., None]) + dark[None, None, :] * checker[..., None]
    albedo = albedo * (0.93 + 0.07 * tile_var[..., None])
    speckle = fbm(size, 96, rng, octaves=2)
    scuffs = contrast(fbm(size, 5, rng, octaves=5, stretch=(3, 0.6)), 0.65, 0.8)
    dirt = contrast(fbm(size, 3, rng, octaves=4), 0.45, 0.9)
    albedo = albedo * (0.94 + 0.08 * speckle[..., None]) * (1 - 0.25 * scuffs[..., None]) * (1 - 0.2 * dirt[..., None])
    albedo = albedo * (1 - 0.5 * seam[..., None])
    height = 0.7 - 0.5 * seam + 0.02 * speckle
    rough = 0.45 + 0.25 * scuffs + 0.15 * dirt
    return albedo, height, rough, 3.0


def diamond_plate(size, rng):
    """Рифлёный стальной лист для антресоли и лестниц."""
    u, v = grid_coords(size)
    n = 12
    cu, cv = np.floor(u * n), np.floor(v * n)
    lx, ly = (u * n) % 1.0 - 0.5, (v * n) % 1.0 - 0.5
    angle = np.where((cu + cv) % 2 == 0, math.pi / 4, -math.pi / 4)
    rx = lx * np.cos(angle) + ly * np.sin(angle)
    ry = -lx * np.sin(angle) + ly * np.cos(angle)
    d = (rx / 0.38) ** 2 + (ry / 0.09) ** 2
    lug = np.clip(1 - d, 0, 1) ** 0.5

    wear = contrast(fbm(size, 4, rng, octaves=4), 0.4, 0.8)
    rust = contrast(fbm(size, 6, rng, octaves=5), 0.7, 0.82)
    steel = np.array((0.50, 0.51, 0.52))
    rust_color = np.array((0.34, 0.20, 0.12))
    albedo = steel[None, None, :] * (0.85 + 0.15 * fbm(size, 48, rng, octaves=2))[..., None]
    albedo = albedo + 0.12 * (lug * wear)[..., None]
    albedo = albedo * (1 - rust[..., None]) + rust_color[None, None, :] * rust[..., None]
    height = 0.3 + 0.6 * lug
    rough = 0.55 - 0.25 * lug * wear + 0.35 * rust
    return np.clip(albedo, 0, 1), height, rough, 5.0


def wood_planks(size, rng):
    """Доски поддонов и ящиков: волокна, щели, гвозди."""
    u, v = grid_coords(size)
    planks = 5
    plank = np.floor(v * planks)
    fy = (v * planks) % 1.0
    gap = contrast(0.03 - np.minimum(fy, 1 - fy), 0, 0.03)
    plank_var = (np.sin((plank + 1) * 78.233) * 43758.5453) % 1.0
    grain = fbm(size, 2, rng, octaves=6, stretch=(1, 24))
    rings = 0.5 + 0.5 * np.sin(grain * 40 + plank_var * 10)
    knots = contrast(fbm(size, 8, rng, octaves=3), 0.8, 0.86)

    wood = np.array((0.55, 0.42, 0.28))
    albedo = wood[None, None, :] * (0.75 + 0.2 * plank_var[..., None] + 0.12 * rings[..., None])
    albedo = albedo * (1 - 0.4 * knots[..., None])
    dirt = contrast(fbm(size, 4, rng, octaves=4), 0.5, 0.9)
    albedo = albedo * (1 - 0.25 * dirt[..., None]) * (1 - 0.8 * gap[..., None])

    nails = np.zeros((size, size))
    for row in range(planks):
        for x in (0.06, 0.94, 0.5):
            cy = (row + 0.5) / planks
            nails += np.exp(-(((u - x) ** 2 + (v - cy) ** 2) / (0.0045 ** 2)))
    nails = np.clip(nails, 0, 1)
    albedo = albedo * (1 - nails[..., None]) + np.array((0.3, 0.28, 0.27))[None, None, :] * nails[..., None]
    height = 0.7 - 0.6 * gap + 0.08 * rings + 0.15 * nails
    rough = 0.8 - 0.3 * nails
    return np.clip(albedo, 0, 1), height, rough, 4.0


def painted_container_metal(size, rng):
    """Крашеный металл (контейнеры, котёл, шкафы): сколы до ржавчины, вмятины."""
    paint = np.array((0.36, 0.13, 0.10))
    rust_color = np.array((0.30, 0.16, 0.08))
    bare = np.array((0.45, 0.45, 0.46))
    chips = contrast(fbm(size, 14, rng, octaves=6), 0.7, 0.73)
    rust = contrast(fbm(size, 5, rng, octaves=5), 0.6, 0.75) * chips
    fade = fbm(size, 3, rng, octaves=4)
    dents = fbm(size, 5, rng, octaves=3)

    albedo = paint[None, None, :] * (0.8 + 0.3 * fade[..., None])
    albedo = albedo * (1 - chips[..., None]) + bare[None, None, :] * chips[..., None]
    albedo = albedo * (1 - rust[..., None]) + rust_color[None, None, :] * rust[..., None]
    height = 0.6 + 0.15 * dents - 0.1 * chips
    rough = 0.55 + 0.1 * fade + 0.3 * rust - 0.1 * (chips - rust)
    return np.clip(albedo, 0, 1), height, rough, 3.0


def drywall(size, rng):
    """Гипсокартон офисов: почти белый, лёгкая фактура, грязь и следы рук."""
    base = 0.74 + 0.03 * (fbm(size, 8, rng) - 0.5)
    texture = fbm(size, 128, rng, octaves=2)
    smudges = contrast(fbm(size, 3, rng, octaves=5), 0.6, 0.9)
    gray = base * (0.97 + 0.04 * texture) * (1 - 0.1 * smudges)
    albedo = tint(gray, (1.0, 0.98, 0.93))
    height = 0.5 + 0.1 * texture
    rough = 0.85 + 0.05 * smudges
    return albedo, height, rough, 1.5


MATERIALS = [
    ("T_Concrete_Floor", concrete_floor, "Пол цеха, рампы и котельной (4×4 м)"),
    ("T_Concrete_BlockWall", concrete_block_wall, "Стены цеха и котельной (2×2 м)"),
    ("T_Corrugated_Metal", corrugated_metal, "Наружные стены, рольставни, навес рампы (2×2 м)"),
    ("T_Asphalt", asphalt, "Двор (4×4 м)"),
    ("T_Office_FloorTiles", office_floor_tiles, "Пол офисов и коридора (2,4×2,4 м)"),
    ("T_Diamond_Plate", diamond_plate, "Антресоль, лестницы, пандусы (1×1 м)"),
    ("T_Wood_Planks", wood_planks, "Поддоны, ящики, стеллажи (1×1 м)"),
    ("T_Painted_Metal", painted_container_metal, "Контейнеры, котёл, шкафчики (2×2 м)"),
    ("T_Drywall", drywall, "Стены офисов (2×2 м)"),
]


# ---------------------------------------------------------------- декали

def wear_mask(size_xy, rng, amount=0.3, cells=24):
    w, h = size_xy
    s = max(w, h)
    noise = fbm(s, cells, rng, octaves=5)[:h, :w]
    return np.clip((noise - amount) / 0.12, 0, 1)


def rgba_from(rgb_img, alpha, rng, wear=0.35):
    a = np.array(alpha, dtype=float) / 255
    a *= wear_mask(rgb_img.size, rng, wear)
    out = rgb_img.convert("RGBA")
    out.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    return out


def decal_hazard_stripes(size, rng):
    w, h = size, size // 4
    img = Image.new("RGB", (w, h), (232, 182, 30))
    draw = ImageDraw.Draw(img)
    step = h
    for x in range(-h, w + h, step):
        draw.polygon([(x, h), (x + step // 2, h), (x + step // 2 + h, 0), (x + h, 0)], fill=(20, 20, 20))
    alpha = Image.new("L", (w, h), 255)
    return rgba_from(img, alpha, rng, 0.22)


def fit_font(draw, text, path, max_w, max_h):
    size = int(max_h)
    while size > 8:
        font = ImageFont.truetype(path, size)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_w and box[3] - box[1] <= max_h:
            return font
        size -= 2
    return ImageFont.truetype(path, size)


def stencil_text(text, size, rng, color=(225, 225, 215), font=FONT_BOLD, wear=0.27, height_ratio=0.35):
    w, h = size, int(size * height_ratio)
    alpha = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(alpha)
    font_obj = fit_font(draw, text, font, w * 0.9, h * 0.7)
    box = draw.textbbox((0, 0), text, font=font_obj)
    tx = (w - (box[2] - box[0])) // 2 - box[0]
    ty = (h - (box[3] - box[1])) // 2 - box[1]
    draw.text((tx, ty), text, fill=255, font=font_obj)
    # Перемычки трафарета: горизонтальные разрывы по высоте букв.
    for frac in (0.5,):
        y = int(ty + box[1] + (box[3] - box[1]) * frac)
        for x in range(0, w, max(4, w // 16)):
            draw.rectangle([x, y - h // 60, x + w // 80, y + h // 60], fill=0)
    alpha = alpha.filter(ImageFilter.GaussianBlur(1.2))
    img = Image.new("RGB", (w, h), color)
    return rgba_from(img, alpha, rng, wear)


def decal_arrow(size, rng):
    img = Image.new("RGB", (size, size), (220, 175, 40))
    alpha = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(alpha)
    s = size
    d.polygon([(0.5 * s, 0.08 * s), (0.85 * s, 0.45 * s), (0.62 * s, 0.45 * s), (0.62 * s, 0.92 * s),
               (0.38 * s, 0.92 * s), (0.38 * s, 0.45 * s), (0.15 * s, 0.45 * s)], fill=255)
    return rgba_from(img, alpha.filter(ImageFilter.GaussianBlur(1)), rng, 0.25)


def decal_oil_stain(size, rng):
    blob = fbm(size, 3, rng, octaves=6)
    u, v = grid_coords(size)
    radial = 1 - np.clip(np.hypot(u - 0.5, v - 0.5) / 0.48, 0, 1)
    a = np.clip((blob * 0.6 + radial * 0.8 - 0.65) / 0.3, 0, 1)
    a = a * (0.6 + 0.4 * fbm(size, 16, rng, octaves=3))
    img = Image.new("RGBA", (size, size), (18, 16, 14, 0))
    img.putalpha(Image.fromarray((a * 230).astype(np.uint8)))
    return img


def decal_sign(size, rng, title, subtitle, bg, fg, border):
    w, h = size, int(size * 0.6)
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    m = w // 24
    d.rectangle([m, m, w - m, h - m], outline=border, width=m // 2)
    f1 = fit_font(d, title, FONT_BOLD, w - 4 * m, h // 5)
    f2 = fit_font(d, subtitle, FONT_BOLD, w - 4 * m, h // 9)
    for text, font, y in ((title, f1, 0.38), (subtitle, f2, 0.66)):
        box = d.textbbox((0, 0), text, font=font)
        d.text(((w - (box[2] - box[0])) // 2 - box[0], int(h * y) - (box[3] - box[1]) // 2 - box[1]), text, fill=fg, font=font)
    # Грязь и выцветание.
    arr = np.array(img, dtype=float) / 255
    dirt = contrast(fbm(w, 4, rng, octaves=5)[:h, :w], 0.4, 0.95)
    arr = arr * (1 - 0.35 * dirt[..., None])
    img = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
    alpha = Image.new("L", (w, h), 255)
    return rgba_from(img, alpha, rng, 0.08)


def make_decals(size, rng):
    return [
        ("D_Hazard_Stripes", decal_hazard_stripes(size, rng), "Края рампы, колонны, ворота (тянется по горизонтали)"),
        ("D_Stencil_Sklad17", stencil_text("СКЛАД 17", size, rng), "Фасад, ворота цеха"),
        ("D_Stencil_B2", stencil_text("B-2", size, rng, color=(230, 190, 40), height_ratio=0.5), "Колонны и стены цеха"),
        ("D_Stencil_Exit", stencil_text("ВЫХОД →", size, rng, color=(220, 220, 210)), "Стены коридора"),
        ("D_Floor_Arrow", decal_arrow(size, rng), "Разметка на полу цеха и рампы"),
        ("D_Oil_Stain", decal_oil_stain(size, rng), "Пятна масла на бетоне и асфальте"),
        ("D_Sign_Caution", decal_sign(size, rng, "ОСТОРОЖНО!", "РАБОТАЕТ ПОГРУЗЧИК", (230, 185, 30), (20, 20, 20), (20, 20, 20)), "Цех, рампа"),
        ("D_Sign_NoEntry", decal_sign(size, rng, "ПОСТОРОННИМ", "ВХОД ЗАПРЕЩЁН", (235, 235, 230), (175, 25, 25), (175, 25, 25)), "Двери офисов, серверная"),
    ]


# ---------------------------------------------------------------- вывод

def to_image(arr):
    return Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8))


def save_material(out_dir, name, albedo, height, rough, strength, size):
    out_dir.mkdir(parents=True, exist_ok=True)
    to_image(albedo).save(out_dir / f"{name}_BaseColor.jpg", quality=92)
    to_image(normal_from_height(height, strength * size / 1024)).save(out_dir / f"{name}_Normal.png", optimize=True)
    to_image(np.clip(rough, 0, 1)).convert("L").save(out_dir / f"{name}_Roughness.jpg", quality=92)


def contact_sheet(root, materials, decals, thumb=256):
    cols = 4
    items = [(n, Image.open(root / "materials" / f"{n}_BaseColor.jpg")) for n, _, _ in materials]
    for n, img, _ in decals:
        bg = Image.new("RGBA", img.size, (90, 90, 90, 255))
        bg.alpha_composite(img)
        items.append((n, bg.convert("RGB")))
    rows = math.ceil(len(items) / cols)
    sheet = Image.new("RGB", (cols * thumb, rows * (thumb + 24)), (21, 24, 28))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(FONT_MONO, 13)
    for i, (name, img) in enumerate(items):
        x, y = (i % cols) * thumb, (i // cols) * (thumb + 24)
        im = img.copy()
        im.thumbnail((thumb - 8, thumb - 8))
        sheet.paste(im, (x + (thumb - im.width) // 2, y + 4 + (thumb - 8 - im.height) // 2))
        d.text((x + 6, y + thumb + 2), name, fill=(220, 220, 215), font=font)
    sheet.save(root / "preview.jpg", quality=88)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--size", type=int, default=1024)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "textures")
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()

    for i, (name, fn, _) in enumerate(MATERIALS):
        rng = np.random.default_rng(args.seed * 1000 + i)
        albedo, height, rough, strength = fn(args.size, rng)
        save_material(args.out / "materials", name, albedo, height, rough, strength, args.size)
        print("material", name)

    decals = make_decals(args.size, np.random.default_rng(args.seed))
    (args.out / "decals").mkdir(parents=True, exist_ok=True)
    for name, img, _ in decals:
        img.save(args.out / "decals" / f"{name}.png", optimize=True)
        print("decal", name)

    contact_sheet(args.out, MATERIALS, decals)
    print("preview", args.out / "preview.jpg")


if __name__ == "__main__":
    main()
