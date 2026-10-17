#!/usr/bin/env python3
"""Готовые блоки для вставки в UEFN через Ctrl+V (BODYCAM для Fortnite).

Unreal Editor умеет вставлять объекты уровня и узлы материалов из текста (формат T3D).
Скрипт собирает три файла в папке paste/:

    01_postprocess.txt  — Post Process Volume с настройками «нагрудной камеры»
    02_fisheye_nodes.txt — узлы материала объектива: «рыбий глаз», кайма, размытие краёв,
                           засветы и тёмные углы (вставлять в редактор материала)
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
        # Цвет как у Bodycam: естественный, чуть тёплый и выцветший, контрастный, светлый.
        "WhiteTemp": "7000.000000",
        "ColorSaturation": "(X=0.850000,Y=0.850000,Z=0.850000,W=0.850000)",
        "ColorContrast": "(X=1.120000,Y=1.120000,Z=1.120000,W=1.120000)",
        "ColorGain": "(X=1.030000,Y=1.000000,Z=0.950000,W=1.000000)",
        "ColorGainShadows": "(X=0.900000,Y=0.900000,Z=0.900000,W=0.900000)",
        # Камера пересвечивает светлое: небо и лампы уходят в белое.
        "AutoExposureBias": "0.800000",
        "BloomIntensity": "2.000000",
        "BloomThreshold": "0.450000",
        "LensFlareIntensity": "0.400000",
        # Кайму, размытие краёв и тёмные углы теперь даёт материал M_Fisheye, тут только добавка.
        "SceneFringeIntensity": "0.500000",
        "ChromaticAberrationStartOffset": "0.400000",
        "VignetteIntensity": "0.300000",
        "FilmGrainIntensity": "0.300000",
        # Экспозиция привыкает к свету медленно, как у камеры.
        "AutoExposureSpeedUp": "1.000000",
        "AutoExposureSpeedDown": "3.000000",
        # Смаз при поворотах.
        "MotionBlurAmount": "0.600000",
        "MotionBlurMax": "6.000000",
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


def lens_block():
    """Объектив нагрудной камеры: сильный «рыбий глаз», цветная кайма и размытие у краёв,
    тёплые засветы и тёмные скруглённые углы. Центр кадра остаётся резким."""
    nodes = []

    def N(cls, x, y, props=(), inputs=("A", "B"), outputs=("Output",)):
        node = Node(len(nodes), cls, x, y, list(props), inputs=inputs, outputs=outputs)
        nodes.append(node)
        return node

    # Координаты экрана относительно центра и квадрат расстояния до центра (0 в центре, 0.5 в углах).
    screen = N("ScreenPosition", -2600, 0, inputs=(), outputs=("ViewportUV", "PixelPosition"))
    centered = N("Subtract", -2350, 0, ["ConstB=0.500000"])
    centered.link("A", screen, "ViewportUV")
    r2 = N("DotProduct", -2150, 300)
    r2.link("A", centered)
    r2.link("B", centered)

    # Три выборки кадра с чуть разной силой изгиба: из них собирается кайма и размытие краёв.
    samples = []
    for i, k in enumerate((0.42, 0.47, 0.52)):
        y = -400 + i * 400
        bend = N("Multiply", -1900, y, [f"ConstB={k:.6f}"])
        bend.link("A", r2)
        factor = N("Add", -1700, y, ["ConstB=1.000000"])
        factor.link("A", bend)
        curved = N("Multiply", -1500, y)
        curved.link("A", centered)
        curved.link("B", factor)
        zoom = N("Multiply", -1300, y, ["ConstB=0.800000"])
        zoom.link("A", curved)
        uv = N("Add", -1100, y, ["ConstB=0.500000"])
        uv.link("A", zoom)
        scene = N("SceneTexture", -900, y, ["SceneTextureId=PPI_PostProcessInput0"],
                  inputs=("UVs",), outputs=("Color", "Size", "InvSize"))
        scene.link("UVs", uv)
        samples.append(scene)

    # Цветная кайма: красный берём с самой изогнутой выборки, синий с самой слабой.
    red = N("ComponentMask", -600, -400, ["R=True"], inputs=("Input",))
    red.link("Input", samples[2], "Color")
    green = N("ComponentMask", -600, -250, ["G=True"], inputs=("Input",))
    green.link("Input", samples[1], "Color")
    blue = N("ComponentMask", -600, -100, ["B=True"], inputs=("Input",))
    blue.link("Input", samples[0], "Color")
    rg = N("AppendVector", -400, -350)
    rg.link("A", red)
    rg.link("B", green)
    fringe = N("AppendVector", -200, -300)
    fringe.link("A", rg)
    fringe.link("B", blue)

    # Размытие к краям: среднее трёх выборок, у центра они почти совпадают.
    sum01 = N("Add", -600, 150)
    sum01.link("A", samples[0], "Color")
    sum01.link("B", samples[1], "Color")
    sum012 = N("Add", -400, 200)
    sum012.link("A", sum01)
    sum012.link("B", samples[2], "Color")
    average = N("Multiply", -200, 200, ["ConstB=0.333333"])
    average.link("A", sum012)
    blurred = N("ComponentMask", 0, 200, ["R=True", "G=True", "B=True"], inputs=("Input",))
    blurred.link("Input", average)
    lens = N("LinearInterpolate", 200, 0, ["ConstAlpha=0.500000"], inputs=("A", "B", "Alpha"))
    lens.link("A", fringe)
    lens.link("B", blurred)

    # Маски: тёмные скруглённые углы и тёплая полоса засвета перед ними.
    corners = N("SmoothStep", -1900, 900, ["ConstMin=0.280000", "ConstMax=0.500000"], inputs=("Min", "Max", "Value"))
    corners.link("Value", r2)
    band = N("SmoothStep", -1900, 1100, ["ConstMin=0.200000", "ConstMax=0.330000"], inputs=("Min", "Max", "Value"))
    band.link("Value", r2)
    open_area = N("OneMinus", -1650, 900, inputs=("Input",))
    open_area.link("Input", corners)
    edge = N("Multiply", -1450, 1100)
    edge.link("A", band)
    edge.link("B", open_area)
    # Засвет только там, где ярко (небо, лампы): умножаем на яркость кадра (зелёный канал).
    brightness = N("ComponentMask", 400, 600, ["G=True"], inputs=("Input",))
    brightness.link("Input", lens)
    leak = N("Multiply", -1300, 1250)
    leak.link("A", edge)
    leak.link("B", brightness)
    leak_r = N("Multiply", -1100, 1000, ["ConstB=0.450000"])
    leak_r.link("A", leak)
    leak_g = N("Multiply", -1100, 1150, ["ConstB=0.180000"])
    leak_g.link("A", leak)
    leak_b = N("Multiply", -1100, 1300, ["ConstB=0.040000"])
    leak_b.link("A", leak)
    leak_rg = N("AppendVector", -950, 1050)
    leak_rg.link("A", leak_r)
    leak_rg.link("B", leak_g)
    leak_rgb = N("AppendVector", -750, 1100)
    leak_rgb.link("A", leak_rg)
    leak_rgb.link("B", leak_b)

    glow = N("Add", 450, 300)
    glow.link("A", lens)
    glow.link("B", leak_rgb)
    darkness = N("Multiply", -1450, 800, ["ConstB=0.920000"])
    darkness.link("A", corners)
    keep = N("OneMinus", -1200, 800, inputs=("Input",))
    keep.link("Input", darkness)
    final = N("Multiply", 700, 300)
    final.link("A", glow)
    final.link("B", keep)

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


# Материалы (имена совпадают с текстурами в textures/materials) и сколько сантиметров покрывает одна текстура.
TEXTURE_SIZE = {
    "T_Concrete_Floor": 400, "T_Concrete_BlockWall": 200, "T_Corrugated_Metal": 200,
    "T_Asphalt": 400, "T_Office_FloorTiles": 240, "T_Diamond_Plate": 100, "T_Wood_Planks": 100,
    "T_Painted_Metal": 200, "T_Drywall": 200, "T_OSB_Plywood": 120, "T_Plaster_Worn": 200,
}
METAL = {"T_Corrugated_Metal": 0.7, "T_Diamond_Plate": 0.7}

CORRUGATED, BLOCK, PLASTER, DRYWALL = "T_Corrugated_Metal", "T_Concrete_BlockWall", "T_Plaster_Worn", "T_Drywall"

# Стены по схеме: (ось, координата, от, до, проёмы [(от, до)], высота, материал). Всё в пикселях схемы.
DOOR = 18  # полуширина обычной двери в px (≈ 230 юнитов)
WALLS = [
    # Внешний контур
    ("h", 40, 40, 680, [], FLOOR_H, CORRUGATED),
    ("h", 520, 40, 680, [], FLOOR_H, CORRUGATED),
    ("v", 40, 40, 520, [], FLOOR_H, CORRUGATED),
    ("v", 680, 40, 520, [], FLOOR_H, CORRUGATED),
    # Двор | рампа, цех, котельная
    ("v", 200, 40, 120, [(80 - DOOR, 80 + DOOR)], FLOOR_H, CORRUGATED),
    ("v", 200, 120, 440, [(280 - DOOR, 280 + DOOR)], HALL_H, CORRUGATED),
    ("v", 200, 440, 520, [(485 - DOOR, 485 + DOOR)], FLOOR_H, CORRUGATED),
    # Рампа | цех: три рольставни
    ("h", 120, 200, 480, [(260 - DOOR, 260 + DOOR), (340 - DOOR, 340 + DOOR), (420 - DOOR, 420 + DOOR)], HALL_H, BLOCK),
    # Цех | котельная
    ("h", 440, 200, 480, [(340 - DOOR, 340 + DOOR)], HALL_H, BLOCK),
    # Цех-блок | офисы
    ("v", 480, 40, 120, [(80 - DOOR, 80 + DOOR)], FLOOR_H, BLOCK),
    ("v", 480, 120, 440, [(220 - DOOR, 220 + DOOR), (340 - DOOR, 340 + DOOR)], HALL_H, BLOCK),
    ("v", 480, 440, 520, [(485 - DOOR, 485 + DOOR)], FLOOR_H, PLASTER),
    # Коридор: облезлая штукатурка, как в подъездах Bodycam
    ("v", 560, 40, 520, [(105 - DOOR, 105 + DOOR), (265 - DOOR, 265 + DOOR), (435 - DOOR, 435 + DOOR)], FLOOR_H, PLASTER),
    ("v", 600, 40, 520, [(115 - DOOR, 115 + DOOR), (245 - DOOR, 245 + DOOR), (405 - DOOR, 405 + DOOR)], FLOOR_H, PLASTER),
    # Перегородки комнат
    ("h", 200, 480, 560, [], FLOOR_H, DRYWALL),
    ("h", 360, 480, 560, [], FLOOR_H, DRYWALL),
    ("h", 200, 600, 680, [], FLOOR_H, DRYWALL),
    ("h", 360, 600, 680, [], FLOOR_H, DRYWALL),
]
DOOR_HEIGHT = 260.0

# Стеллажи и укрытия: (подпись, x, y, ширина, глубина в px, высота в юнитах, материал)
PROPS = [
    ("Rack_W_N", 250, 170, 20, 70, 300, "T_Wood_Planks"), ("Rack_W_S", 250, 320, 20, 80, 300, "T_Wood_Planks"),
    ("Rack_C_N", 330, 170, 20, 70, 300, "T_Wood_Planks"), ("Rack_C_S", 330, 320, 20, 80, 300, "T_Wood_Planks"),
    ("Rack_E_N", 410, 210, 20, 30, 300, "T_Wood_Planks"), ("Rack_E_S", 410, 320, 20, 80, 300, "T_Wood_Planks"),
    ("Container_Yard_N", 110, 70, 70, 26, 260, "T_Painted_Metal"),
    ("Truck_Yard", 140, 230, 30, 100, 350, "T_Painted_Metal"),
    ("Container_Yard_S", 150, 430, 26, 70, 260, "T_Painted_Metal"),
    ("Pallets_Dock", 300, 60, 50, 22, 120, "T_Wood_Planks"),
    ("Boiler", 270, 465, 60, 16, 200, "T_Painted_Metal"),
    ("Pipes_Boiler", 360, 490, 16, 22, 180, "T_Painted_Metal"),
    # Перегородки из OSB в проходе цеха, как в тренировочном ангаре Bodycam
    ("OSB_1", 280, 268, 40, 1, 240, "T_OSB_Plywood"),
    ("OSB_2", 360, 290, 40, 1, 240, "T_OSB_Plywood"),
    ("OSB_3", 440, 250, 1, 50, 240, "T_OSB_Plywood"),
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


def warehouse_boxes():
    """Вся геометрия карты: список блоков (подпись, папка, материал, центр, размеры, угол пандуса)."""
    boxes = []

    def add(label, folder, mat, cx, cy, cz, sx, sy, sz, ramp=None):
        boxes.append(dict(label=f"{label}_{len(boxes) + 1:03d}", folder=folder, mat=mat,
                          c=(cx, cy, cz), s=(sx, sy, sz), ramp=ramp))

    for axis, at, start, end, gaps, height, mat in WALLS:
        for _, _, a, b, z0, z1 in wall_segments(axis, at, start, end, gaps, height):
            length = (b - a) * PX
            mid = uu((a + b) / 2)
            if axis == "h":
                add("Wall", "Walls", mat, mid, uu(at), (z0 + z1) / 2, length, WALL_T, z1 - z0)
            else:
                add("Wall", "Walls", mat, uu(at), mid, (z0 + z1) / 2, WALL_T, length, z1 - z0)

    # Полы (верх на 2 юнита выше сетки Fortnite, чтобы не мерцало)
    floors = [
        ("Floor_Yard", 40, 40, 200, 520, "T_Asphalt"),
        ("Floor_Dock", 200, 40, 480, 120, "T_Concrete_Floor"),
        ("Floor_Hall", 200, 120, 480, 440, "T_Concrete_Floor"),
        ("Floor_Boiler", 200, 440, 480, 520, "T_Concrete_Floor"),
        ("Floor_Offices", 480, 40, 680, 520, "T_Office_FloorTiles"),
    ]
    for label, x0, y0, x1, y1, mat in floors:
        add(label, "Floors", mat, uu((x0 + x1) / 2), uu((y0 + y1) / 2), -8.0, (x1 - x0) * PX, (y1 - y0) * PX, 20.0)

    # Крыши: без них в помещения попадает лунный свет
    roofs = [
        ("Roof_Dock", 200, 40, 480, 120, FLOOR_H),
        ("Roof_Hall", 200, 120, 480, 440, HALL_H),
        ("Roof_Boiler", 200, 440, 480, 520, FLOOR_H),
        ("Roof_Offices", 480, 40, 680, 520, FLOOR_H),
    ]
    for label, x0, y0, x1, y1, z in roofs:
        add(label, "Roofs", CORRUGATED, uu((x0 + x1) / 2), uu((y0 + y1) / 2), z + 10.0, (x1 - x0) * PX, (y1 - y0) * PX, 20.0)

    # Антресоль: Г-образная, вдоль северной и западной стены цеха
    add("Mezzanine_N", "Mezzanine", "T_Diamond_Plate", uu(340), uu(141), FLOOR_H - 10.0, 272 * PX, 34 * PX, 20.0)
    add("Mezzanine_W", "Mezzanine", "T_Diamond_Plate", uu(221), uu(259), FLOOR_H - 10.0, 34 * PX, 202 * PX, 20.0)
    add("Railing_N", "Mezzanine", "T_Painted_Metal", uu(340), uu(158), FLOOR_H + 50.0, 200 * PX, 8.0, 100.0)
    add("Railing_W", "Mezzanine", "T_Painted_Metal", uu(238), uu(259), FLOOR_H + 50.0, 8.0, 202 * PX, 100.0)

    # Пандусы на антресоль: оба поднимаются к северу (наклонённые плиты)
    for label, cx, cy, length_px, width_px in (("Ramp_NE", 460, 179, 42, 34), ("Ramp_SW", 221, 380, 40, 34)):
        run = length_px * PX
        angle = math.degrees(math.atan2(FLOOR_H, run))
        add(label, "Mezzanine", "T_Diamond_Plate", uu(cx), uu(cy), FLOOR_H / 2,
            width_px * PX, math.hypot(run, FLOOR_H), 20.0, ramp=angle)

    # Стеллажи, укрытия и перегородки (минимальная толщина 12 юнитов)
    for label, x, y, w, d, h, mat in PROPS:
        add(label, "Cover", mat, uu(x + w / 2), uu(y + d / 2), h / 2, max(w * PX, 12.0), max(d * PX, 12.0), h)

    return boxes


def warehouse_block(cube):
    actors = []
    for b in warehouse_boxes():
        text = cube_actor(b["label"], b["folder"], *b["c"], *b["s"], cube)
        if b["ramp"] is not None:
            text = text.replace("            RelativeScale3D",
                                f"            RelativeRotation=(Pitch=0.000000,Yaw=0.000000,Roll={b['ramp']:.4f})\n            RelativeScale3D")
        actors.append(text)
    actors.append(lights_actors())
    return "Begin Map\n   Begin Level\n" + "".join(actors) + "   End Level\nBegin Surface\nEnd Surface\nEnd Map\n"


def lights_actors():
    return "".join(light_actor(label, "Lights/Flicker" if flicker else "Lights", uu(x), uu(y), z, color, intensity, radius)
                   for label, x, y, z, color, intensity, radius, flicker in LIGHTS)


def lights_block():
    return "Begin Map\n   Begin Level\n" + lights_actors() + "   End Level\nBegin Surface\nEnd Surface\nEnd Map\n"


# ---------------------------------------------------------------- 4. карта одним OBJ с текстурами

def box_corners(b):
    """8 вершин блока в юнитах UEFN (X восток, Y юг, Z вверх). Пандус наклонён: северный край выше."""
    (cx, cy, cz), (sx, sy, sz) = b["c"], b["s"]
    ex, ey, ez = (1, 0, 0), (0, 1, 0), (0, 0, 1)
    if b["ramp"] is not None:
        a = math.radians(b["ramp"])
        ey = (0, -math.cos(a), math.sin(a))   # вдоль пандуса: на север и вверх
        ez = (0, math.sin(a), math.cos(a))    # толщина плиты
        ey = tuple(-v for v in ey)            # +Y локально = южный (нижний) край
    corners = []
    for dx in (-0.5, 0.5):
        for dy in (-0.5, 0.5):
            for dz in (-0.5, 0.5):
                corners.append(tuple(c + dx * sx * e1 + dy * sy * e2 + dz * sz * e3
                                     for c, e1, e2, e3 in zip((cx, cy, cz), ex, ey, ez)))
    return corners


BOX_FACES = [  # индексы углов (dx, dy, dz) → 4 вершины на грань, порядок обхода по кругу
    (0, 1, 3, 2), (4, 6, 7, 5),   # -X, +X
    (0, 4, 5, 1), (2, 3, 7, 6),   # -Y, +Y
    (0, 2, 6, 4), (1, 5, 7, 3),   # -Z, +Z
]


def warehouse_obj():
    """OBJ (Y вверх, сантиметры) и MTL. Каждая грань записана в обе стороны, поэтому стены видны
    при любом развороте осей при импорте. UV в мировом масштабе: текстура не растягивается."""
    boxes = warehouse_boxes()
    v_lines, vt_lines, vn_lines, faces_by_mat = [], [], [], {}

    def to_obj(p):
        x, y, z = p
        return (x, z, y)

    for b in boxes:
        tile = TEXTURE_SIZE[b["mat"]]
        corners = box_corners(b)
        for face in BOX_FACES:
            pts = [corners[i] for i in face]
            a, bb, c = pts[0], pts[1], pts[2]
            u = [bb[i] - a[i] for i in range(3)]
            w = [c[i] - a[i] for i in range(3)]
            n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
            length = math.sqrt(sum(k * k for k in n)) or 1.0
            n = [k / length for k in n]
            axis = max(range(3), key=lambda i: abs(n[i]))
            uv_axes = [i for i in range(3) if i != axis]
            base = len(v_lines)
            for p in pts:
                v_lines.append("v {:.2f} {:.2f} {:.2f}".format(*to_obj(p)))
                vt_lines.append("vt {:.4f} {:.4f}".format(p[uv_axes[0]] / tile, p[uv_axes[1]] / tile))
            nf = len(vn_lines)
            vn_lines.append("vn {:.4f} {:.4f} {:.4f}".format(*to_obj(n)))
            vn_lines.append("vn {:.4f} {:.4f} {:.4f}".format(*to_obj([-k for k in n])))
            idx = [base + i + 1 for i in range(4)]
            front = " ".join(f"{i}/{i}/{nf + 1}" for i in idx)
            back = " ".join(f"{i}/{i}/{nf + 2}" for i in reversed(idx))
            faces_by_mat.setdefault(b["mat"], []).extend([f"f {front}", f"f {back}"])

    obj = ["# Склад 17 — BODYCAM для Fortnite. Сгенерировано tools/generate_paste.py",
           "mtllib Warehouse17.mtl", "o Warehouse17"]
    obj += v_lines + vt_lines + vn_lines
    for mat, faces in faces_by_mat.items():
        obj.append(f"usemtl {mat}")
        obj += faces
    mtl = []
    for mat in faces_by_mat:
        tex = f"../textures/materials/{mat}"
        mtl += [f"newmtl {mat}", "Kd 1.000 1.000 1.000", "Ks 0.000 0.000 0.000",
                f"Pm {METAL.get(mat, 0.0):.2f}",
                f"map_Kd {tex}_BaseColor.jpg",
                f"map_Bump {tex}_Normal.png",
                f"norm {tex}_Normal.png",
                f"map_Pr {tex}_Roughness.jpg", ""]
    return "\n".join(obj) + "\n", "\n".join(mtl)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cube", default="/Engine/BasicShapes/Cube.Cube",
                        help="путь к мешу-кубу 100×100×100 (правый клик по мешу → Copy Reference)")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "paste")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "01_postprocess.txt").write_text(postprocess_block(), encoding="utf-8")
    (args.out / "02_fisheye_nodes.txt").write_text(lens_block(), encoding="utf-8")
    (args.out / "03_warehouse17.txt").write_text(warehouse_block(args.cube), encoding="utf-8")
    (args.out / "04_lights.txt").write_text(lights_block(), encoding="utf-8")
    map_dir = args.out.parent / "map"
    map_dir.mkdir(exist_ok=True)
    obj, mtl = warehouse_obj()
    (map_dir / "Warehouse17.obj").write_text(obj, encoding="utf-8")
    (map_dir / "Warehouse17.mtl").write_text(mtl, encoding="utf-8")
    print(map_dir / "Warehouse17.obj", len(obj), "bytes")
    for f in sorted(args.out.glob("*.txt")):
        print(f, f.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
