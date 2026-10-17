#!/usr/bin/env python3
"""Готовые блоки для вставки в UEFN через Ctrl+V (BODYCAM для Fortnite).

Unreal Editor умеет вставлять объекты уровня и узлы материалов из текста (формат T3D).
Скрипт собирает три файла в папке paste/:

    01_postprocess.txt  — Post Process Volume с настройками «нагрудной камеры»
    02_fisheye_nodes.txt — узлы материала «рыбий глаз» (вставлять в редактор материала)
    03_warehouse17.txt  — коробка карты «Склад 17»: стены, полы, крыши, антресоль,
                           стеллажи, укрытия и лампы

    python3 tools/generate_paste.py
    python3 tools/generate_paste.py --cube /Engine/BasicShapes/Cube.Cube
"""

import argparse
import math
import uuid
from pathlib import Path

TILE = 512.0          # клетка Fortnite, юниты
PX = TILE / 40.0      # 1 px схемы map_warehouse17.svg = 12.8 юнита
ORIGIN = 40.0         # отступ схемы в пикселях
FLOOR_H = 384.0       # высота этажа
HALL_H = 768.0        # высота цеха
WALL_T = 20.0         # толщина стен
CUBE = 100.0          # размер стандартного куба движка


def guid():
    return uuid.uuid4().hex.upper()


def uu(px):
    """Пиксели схемы → юниты UEFN (X на восток, Y на юг)."""
    return (px - ORIGIN) * PX


# ---------------------------------------------------------------- 1. постобработка

def postprocess_block():
    settings = {
        # Цвет: почти без насыщенности, жёсткий контраст, без ночной синевы.
        "WhiteTemp": "7500.000000",
        "ColorSaturation": "(X=0.450000,Y=0.450000,Z=0.450000,W=0.450000)",
        "ColorContrast": "(X=1.300000,Y=1.300000,Z=1.300000,W=1.300000)",
        "ColorGain": "(X=1.050000,Y=1.000000,Z=0.800000,W=1.000000)",
        "ColorGainShadows": "(X=0.850000,Y=0.850000,Z=0.850000,W=0.850000)",
        # Объектив дешёвой камеры.
        "BloomIntensity": "1.500000",
        "BloomThreshold": "0.600000",
        "SceneFringeIntensity": "1.200000",
        "ChromaticAberrationStartOffset": "0.250000",
        "VignetteIntensity": "1.000000",
        "FilmGrainIntensity": "0.700000",
        "LensFlareIntensity": "0.300000",
        # Экспозиция привыкает к свету медленно, как у камеры.
        "AutoExposureSpeedUp": "1.000000",
        "AutoExposureSpeedDown": "3.000000",
        # Смаз при поворотах.
        "MotionBlurAmount": "0.800000",
        "MotionBlurMax": "8.000000",
    }
    parts = []
    for key, value in settings.items():
        parts.append(f"bOverride_{key}=True")
        parts.append(f"{key}={value}")
    settings_text = ",".join(parts)
    return f"""Begin Map
   Begin Level
      Begin Actor Class=/Script/Engine.PostProcessVolume Name=BodycamPostProcess Archetype=/Script/Engine.PostProcessVolume'/Script/Engine.Default__PostProcessVolume'
         Settings=({settings_text})
         bUnbound=True
         Priority=10.000000
         ActorLabel="Bodycam_PostProcess"
         FolderPath="Bodycam"
      End Actor
   End Level
Begin Surface
End Surface
End Map
"""


# ---------------------------------------------------------------- 2. узлы «рыбьего глаза»

class Node:
    def __init__(self, idx, cls, x, y, props=None, inputs=(), outputs=("Output",)):
        self.name = f"MaterialGraphNode_{idx}"
        self.expr = f"MaterialExpression{cls}_{idx}"
        self.cls = cls
        self.x, self.y = x, y
        self.props = props or []
        self.inputs = {n: guid() for n in inputs}
        self.outputs = {n: guid() for n in outputs}
        self.in_links = {}   # имя входа -> (узел, имя выхода)
        self.out_links = {n: [] for n in outputs}

    def link(self, input_name, src, output_name="Output"):
        self.in_links[input_name] = (src, output_name)
        src.out_links[output_name].append((self, input_name))


def pin(pin_id, name, direction_out, links, default=None):
    linked = "".join(f"{n} {p}," for n, p in links)
    fields = [
        f"PinId={pin_id}",
        f'PinName="{name}"',
    ]
    if direction_out:
        fields.append('Direction="EGPD_Output"')
    fields += [
        'PinType.PinCategory="{}"'.format("" if direction_out else "required"),
        'PinType.PinSubCategory=""',
        "PinType.PinSubCategoryObject=None",
        "PinType.PinSubCategoryMemberReference=()",
        "PinType.PinValueType=()",
        "PinType.ContainerType=None",
        "PinType.bIsReference=False",
        "PinType.bIsConst=False",
        "PinType.bIsWeakPointer=False",
        "PinType.bIsUObjectWrapper=False",
        "PinType.bSerializeAsSinglePrecisionFloat=False",
    ]
    if default is not None:
        fields.append(f'DefaultValue="{default}"')
    if links:
        fields.append(f"LinkedTo=({linked})")
    fields += [
        "PersistentGuid=00000000000000000000000000000000",
        "bHidden=False",
        "bNotConnectable=False",
        "bDefaultValueIsReadOnly=False",
        "bDefaultValueIsIgnored=False",
        "bAdvancedView=False",
        "bOrphanedPin=False",
    ]
    return "   CustomProperties Pin (" + ",".join(fields) + ",)"


MATERIAL = "M_Fisheye"


def node_text(n, nodes_by_name):
    graph = f"/Engine/Transient.{MATERIAL}:MaterialGraph_0"
    node_path = f"/Script/UnrealEd.MaterialGraphNode'{graph}.{n.name}'"
    expr_path = f"/Script/Engine.MaterialExpression{n.cls}'{graph}.{n.name}.{n.expr}'"
    lines = [f'Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="{n.name}" ExportPath="{node_path}"']
    lines.append(f'   Begin Object Class=/Script/Engine.MaterialExpression{n.cls} Name="{n.expr}" ExportPath="{expr_path}"')
    lines.append("   End Object")
    lines.append(f'   Begin Object Name="{n.expr}" ExportPath="{expr_path}"')
    for inp, (src, out) in n.in_links.items():
        out_index = list(src.outputs).index(out)
        prop = "Coordinates" if inp == "UVs" else inp
        index = f",OutputIndex={out_index}" if out_index else ""
        lines.append(f'      {prop}=(Expression="/Script/Engine.MaterialExpression{src.cls}\'{src.name}.{src.expr}\'"{index})')
    for p in n.props:
        lines.append(f"      {p}")
    lines.append(f"      MaterialExpressionEditorX={n.x}")
    lines.append(f"      MaterialExpressionEditorY={n.y}")
    lines.append(f"      MaterialExpressionGuid={guid()}")
    lines.append(f'      Material="/Script/UnrealEd.PreviewMaterial\'/Engine/Transient.{MATERIAL}\'"')
    lines.append("   End Object")
    lines.append(f'   MaterialExpression="/Script/Engine.MaterialExpression{n.cls}\'{n.expr}\'"')
    lines.append(f"   NodePosX={n.x}")
    lines.append(f"   NodePosY={n.y}")
    lines.append(f"   NodeGuid={guid()}")
    for i, (name, pid) in enumerate(n.inputs.items()):
        links = []
        if name in n.in_links:
            src, out = n.in_links[name]
            links = [(src.name, src.outputs[out])]
        lines.append(pin(pid, name, False, links))
    for i, (name, pid) in enumerate(n.outputs.items()):
        links = [(dst.name, dst.inputs[inp]) for dst, inp in n.out_links[name]]
        lines.append(pin(pid, name, True, links))
    lines.append("End Object")
    return "\n".join(lines)


def fisheye_block():
    # UV экрана → центрируем → r² → коэффициент (1 + k·r²) → масштаб → обратно в 0..1 → выборка кадра.
    screen = Node(0, "ScreenPosition", -1400, 0, outputs=("ViewportUV", "PixelPosition"))
    centered = Node(1, "Subtract", -1150, 0, ["ConstB=0.500000"], inputs=("A", "B"))
    r2 = Node(2, "DotProduct", -950, 120, inputs=("A", "B"))
    k = Node(3, "Multiply", -750, 120, ["ConstB=0.250000"], inputs=("A", "B"))
    one_plus = Node(4, "Add", -550, 120, ["ConstB=1.000000"], inputs=("A", "B"))
    scaled = Node(5, "Multiply", -350, 0, inputs=("A", "B"))
    zoom = Node(6, "Multiply", -150, 0, ["ConstB=0.880000"], inputs=("A", "B"))
    uv = Node(7, "Add", 50, 0, ["ConstB=0.500000"], inputs=("A", "B"))
    scene = Node(8, "SceneTexture", 250, 0, ["SceneTextureId=PPI_PostProcessInput0"],
                 inputs=("UVs",), outputs=("Color", "Size", "InvSize"))

    centered.link("A", screen, "ViewportUV")
    r2.link("A", centered)
    r2.link("B", centered)
    k.link("A", r2)
    one_plus.link("A", k)
    scaled.link("A", centered)
    scaled.link("B", one_plus)
    zoom.link("A", scaled)
    uv.link("A", zoom)
    scene.link("UVs", uv)

    nodes = [screen, centered, r2, k, one_plus, scaled, zoom, uv, scene]
    by_name = {n.name: n for n in nodes}
    return "\n".join(node_text(n, by_name) for n in nodes) + "\n"


# ---------------------------------------------------------------- 3. коробка карты

def cube_actor(label, folder, cx, cy, cz, sx, sy, sz, cube_path):
    """Куб с центром (cx, cy, cz) в юнитах и размерами sx × sy × sz."""
    name = label.replace(" ", "_")
    return f"""      Begin Actor Class=/Script/Engine.StaticMeshActor Name={name} Archetype=/Script/Engine.StaticMeshActor'/Script/Engine.Default__StaticMeshActor'
         Begin Object Class=/Script/Engine.StaticMeshComponent Name="StaticMeshComponent0" Archetype=/Script/Engine.StaticMeshComponent'/Script/Engine.Default__StaticMeshActor:StaticMeshComponent0'
         End Object
         Begin Object Name="StaticMeshComponent0"
            StaticMesh=/Script/Engine.StaticMesh'{cube_path}'
            RelativeLocation=(X={cx:.1f},Y={cy:.1f},Z={cz:.1f})
            RelativeScale3D=(X={sx / CUBE:.4f},Y={sy / CUBE:.4f},Z={sz / CUBE:.4f})
         End Object
         StaticMeshComponent=StaticMeshComponent0
         RootComponent=StaticMeshComponent0
         ActorLabel="{label}"
         FolderPath="Warehouse17/{folder}"
      End Actor
"""


def light_actor(label, folder, x, y, z, color, intensity, radius):
    r, g, b = color
    return f"""      Begin Actor Class=/Script/Engine.PointLight Name={label} Archetype=/Script/Engine.PointLight'/Script/Engine.Default__PointLight'
         Begin Object Class=/Script/Engine.PointLightComponent Name="LightComponent0" Archetype=/Script/Engine.PointLightComponent'/Script/Engine.Default__PointLight:LightComponent0'
         End Object
         Begin Object Name="LightComponent0"
            Intensity={intensity:.6f}
            IntensityUnits=Candelas
            LightColor=(B={b},G={g},R={r},A=255)
            AttenuationRadius={radius:.6f}
            RelativeLocation=(X={x:.1f},Y={y:.1f},Z={z:.1f})
         End Object
         PointLightComponent=LightComponent0
         LightComponent=LightComponent0
         RootComponent=LightComponent0
         ActorLabel="{label}"
         FolderPath="Warehouse17/{folder}"
      End Actor
"""


# Стены по схеме: (ось, координата, от, до, проёмы [(от, до)], высота). Всё в пикселях схемы.
DOOR = 18  # полуширина обычной двери в px (≈ 230 юнитов)
WALLS = [
    # Внешний контур
    ("h", 40, 40, 680, [], FLOOR_H),
    ("h", 520, 40, 680, [], FLOOR_H),
    ("v", 40, 40, 520, [], FLOOR_H),
    ("v", 680, 40, 520, [], FLOOR_H),
    # Двор | рампа, цех, котельная
    ("v", 200, 40, 120, [(80 - DOOR, 80 + DOOR)], FLOOR_H),
    ("v", 200, 120, 440, [(280 - DOOR, 280 + DOOR)], HALL_H),
    ("v", 200, 440, 520, [(485 - DOOR, 485 + DOOR)], FLOOR_H),
    # Рампа | цех: три рольставни
    ("h", 120, 200, 480, [(260 - DOOR, 260 + DOOR), (340 - DOOR, 340 + DOOR), (420 - DOOR, 420 + DOOR)], HALL_H),
    # Цех | котельная
    ("h", 440, 200, 480, [(340 - DOOR, 340 + DOOR)], HALL_H),
    # Цех-блок | офисы
    ("v", 480, 40, 120, [(80 - DOOR, 80 + DOOR)], FLOOR_H),
    ("v", 480, 120, 440, [(220 - DOOR, 220 + DOOR), (340 - DOOR, 340 + DOOR)], HALL_H),
    ("v", 480, 440, 520, [(485 - DOOR, 485 + DOOR)], FLOOR_H),
    # Коридор
    ("v", 560, 40, 520, [(105 - DOOR, 105 + DOOR), (265 - DOOR, 265 + DOOR), (435 - DOOR, 435 + DOOR)], FLOOR_H),
    ("v", 600, 40, 520, [(115 - DOOR, 115 + DOOR), (245 - DOOR, 245 + DOOR), (405 - DOOR, 405 + DOOR)], FLOOR_H),
    # Перегородки комнат
    ("h", 200, 480, 560, [], FLOOR_H),
    ("h", 360, 480, 560, [], FLOOR_H),
    ("h", 200, 600, 680, [], FLOOR_H),
    ("h", 360, 600, 680, [], FLOOR_H),
]
DOOR_HEIGHT = 260.0

# Стеллажи и укрытия: (подпись, x, y, ширина, глубина в px, высота в юнитах)
PROPS = [
    ("Rack_W_N", 250, 170, 20, 70, 300), ("Rack_W_S", 250, 320, 20, 80, 300),
    ("Rack_C_N", 330, 170, 20, 70, 300), ("Rack_C_S", 330, 320, 20, 80, 300),
    ("Rack_E_N", 410, 210, 20, 30, 300), ("Rack_E_S", 410, 320, 20, 80, 300),
    ("Container_Yard_N", 110, 70, 70, 26, 260),
    ("Truck_Yard", 140, 230, 30, 100, 350),
    ("Container_Yard_S", 150, 430, 26, 70, 260),
    ("Pallets_Dock", 300, 60, 50, 22, 120),
    ("Boiler", 270, 465, 60, 16, 200),
    ("Pipes_Boiler", 360, 490, 16, 22, 180),
]

SODIUM = (255, 150, 60)
FLUO = (220, 240, 255)
# (подпись, x, y в px, высота, цвет, сила, радиус, мерцающая)
LIGHTS = [
    ("Lamp_Yard_N", 186, 56, 600, SODIUM, 40, 2500, False),
    ("Lamp_Yard_S", 186, 506, 600, SODIUM, 40, 2500, False),
    ("Lamp_Dock", 420, 72, 330, SODIUM, 20, 1500, False),
    ("Lamp_Hall_N", 300, 190, 720, FLUO, 30, 2000, False),
    ("Lamp_Corridor_N", 580, 160, 340, FLUO, 12, 1000, False),
    ("Lamp_Locker", 640, 348, 340, FLUO, 12, 1000, False),
    ("Flicker_Hall_SE", 380, 360, 720, FLUO, 25, 1800, True),
    ("Flicker_Boiler", 420, 500, 330, SODIUM, 8, 900, True),
    ("Flicker_Corridor_S", 580, 400, 340, FLUO, 12, 1000, True),
]


def wall_segments(axis, at, start, end, gaps, height):
    """Разбивает стену на куски вокруг проёмов. Над каждой дверью остаётся перемычка."""
    pieces = []
    cursor = start
    for g0, g1 in sorted(gaps):
        if g0 > cursor:
            pieces.append((cursor, g0, 0.0, height))
        pieces.append((g0, g1, DOOR_HEIGHT, height))   # перемычка над дверью
        cursor = g1
    if end > cursor:
        pieces.append((cursor, end, 0.0, height))
    return [(axis, at, a, b, z0, z1) for a, b, z0, z1 in pieces if z1 > z0]


def warehouse_block(cube):
    actors = []
    n = 0

    def add(label, folder, cx, cy, cz, sx, sy, sz):
        nonlocal n
        n += 1
        actors.append(cube_actor(f"{label}_{n:03d}", folder, cx, cy, cz, sx, sy, sz, cube))

    # Стены
    for axis, at, start, end, gaps, height in WALLS:
        for _, _, a, b, z0, z1 in wall_segments(axis, at, start, end, gaps, height):
            length = (b - a) * PX
            mid = uu((a + b) / 2)
            if axis == "h":
                add("Wall", "Walls", mid, uu(at), (z0 + z1) / 2, length, WALL_T, z1 - z0)
            else:
                add("Wall", "Walls", uu(at), mid, (z0 + z1) / 2, WALL_T, length, z1 - z0)

    # Полы (верх на 2 юнита выше сетки Fortnite, чтобы не мерцало)
    floors = [
        ("Floor_Yard", 40, 40, 200, 520),
        ("Floor_Dock", 200, 40, 480, 120),
        ("Floor_Hall", 200, 120, 480, 440),
        ("Floor_Boiler", 200, 440, 480, 520),
        ("Floor_Offices", 480, 40, 680, 520),
    ]
    for label, x0, y0, x1, y1 in floors:
        add(label, "Floors", uu((x0 + x1) / 2), uu((y0 + y1) / 2), -8.0, (x1 - x0) * PX, (y1 - y0) * PX, 20.0)

    # Крыши: без них в помещения попадает лунный свет
    roofs = [
        ("Roof_Dock", 200, 40, 480, 120, FLOOR_H),
        ("Roof_Hall", 200, 120, 480, 440, HALL_H),
        ("Roof_Boiler", 200, 440, 480, 520, FLOOR_H),
        ("Roof_Offices", 480, 40, 680, 520, FLOOR_H),
    ]
    for label, x0, y0, x1, y1, z in roofs:
        add(label, "Roofs", uu((x0 + x1) / 2), uu((y0 + y1) / 2), z + 10.0, (x1 - x0) * PX, (y1 - y0) * PX, 20.0)

    # Антресоль: Г-образная, вдоль северной и западной стены цеха
    add("Mezzanine_N", "Mezzanine", uu(340), uu(141), FLOOR_H - 10.0, 272 * PX, 34 * PX, 20.0)
    add("Mezzanine_W", "Mezzanine", uu(221), uu(259), FLOOR_H - 10.0, 34 * PX, 202 * PX, 20.0)
    add("Railing_N", "Mezzanine", uu(340), uu(158), FLOOR_H + 50.0, 200 * PX, 8.0, 100.0)
    add("Railing_W", "Mezzanine", uu(238), uu(259), FLOOR_H + 50.0, 8.0, 202 * PX, 100.0)

    # Пандусы на антресоль: оба поднимаются к северу (наклонённые плиты)
    ramps = [
        # (подпись, центр x, центр y в px, длина в px, ширина в px, ось подъёма)
        ("Ramp_NE", 460, 179, 42, 34, "y"),
        ("Ramp_SW", 221, 380, 40, 34, "y"),
    ]
    ramp_text = []
    for label, cx, cy, length_px, width_px, _ in ramps:
        run = length_px * PX
        angle = math.degrees(math.atan2(FLOOR_H, run))
        slope_len = math.hypot(run, FLOOR_H)
        n += 1
        ramp_text.append(cube_actor(f"{label}_{n:03d}", "Mezzanine", uu(cx), uu(cy), FLOOR_H / 2,
                                    width_px * PX, slope_len, 20.0, cube)
                         .replace("            RelativeScale3D",
                                  f"            RelativeRotation=(Pitch=0.000000,Yaw=0.000000,Roll={angle:.4f})\n            RelativeScale3D"))
    actors += ramp_text

    # Стеллажи и укрытия
    for label, x, y, w, d, h in PROPS:
        add(label, "Cover", uu(x + w / 2), uu(y + d / 2), h / 2, w * PX, d * PX, h)

    # Свет
    for label, x, y, z, color, intensity, radius, flicker in LIGHTS:
        folder = "Lights/Flicker" if flicker else "Lights"
        actors.append(light_actor(label, folder, uu(x), uu(y), z, color, intensity, radius))

    return "Begin Map\n   Begin Level\n" + "".join(actors) + "   End Level\nBegin Surface\nEnd Surface\nEnd Map\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cube", default="/Engine/BasicShapes/Cube.Cube",
                        help="путь к мешу-кубу 100×100×100 (правый клик по мешу → Copy Reference)")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "paste")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "01_postprocess.txt").write_text(postprocess_block(), encoding="utf-8")
    (args.out / "02_fisheye_nodes.txt").write_text(fisheye_block(), encoding="utf-8")
    (args.out / "03_warehouse17.txt").write_text(warehouse_block(args.cube), encoding="utf-8")
    for f in sorted(args.out.glob("*.txt")):
        print(f, f.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
