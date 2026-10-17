#!/usr/bin/env python3
"""Точки появления игрока для «Склада 17» (вставка в UEFN через Ctrl+V).

Берёт образец спавна, скопированный из UEFN (tools/templates/player_spawner.t3d), и собирает:

    paste/06_spawns_lobby.txt  — 10 спавнов в брифинге (лобби), для всех режимов
    paste/07_spawns_teams.txt  — ALPHA и BRAVO по 6 (Раунды берут первые 5, командный бой все 6)
    paste/08_spawns_ffa.txt    — 12 спавнов по всей карте (Deathmatch и Гонка вооружений)

Координаты те же, что в docs/MAP.md: X — восток, Y — юг, юниты UEFN.

    python3 tools/generate_spawners.py
"""

import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "tools" / "templates" / "player_spawner.t3d"
PASTE = ROOT / "paste"

TEMPLATE_NAME = "BP_Creative_Player_Spawner_Prop_C_UAID_40C73C33DC6C120C03_1596495725"
FLOOR_Z = 5.0           # верх плит пола +2, чуть выше, чтобы спавн не утонул
HALL_CENTER = (3328.0, 2912.0)

# Брифинг: между скамейками, лицом на восток к доске с планом (как LOBBY_SPAWNS в generate_paste.py).
LOBBY = [("SP_Lobby_%d" % (i + 1), 9450 + col * 260, 1850 + row * 260, 0.0)
         for i, (row, col) in enumerate([(r, c) for r in range(3) for c in range(4)][:10])]

# ALPHA во дворе смотрит на восток, BRAVO в раздевалке — на запад. Шестые — для командного боя.
ALPHA = [(320, 2240), (704, 2240), (512, 3072), (320, 3904), (704, 3904), (2432, 448)]
BRAVO = [(7424, 2656), (7936, 2656), (7680, 3232), (7424, 3776), (7936, 3776), (5376, 5728)]
TEAMS = ([("SP_Alpha_%d" % (i + 1), x, y, 0.0) for i, (x, y) in enumerate(ALPHA)]
         + [("SP_Bravo_%d" % (i + 1), x, y, 180.0) for i, (x, y) in enumerate(BRAVO)])

# Deathmatch и Гонка: по всей карте, лицом к центру цеха.
FFA_POINTS = [(384, 496), (256, 5600), (2432, 448), (5376, 448), (3328, 2912), (4352, 1888),
              (3328, 4832), (5376, 5728), (6144, 480), (6144, 5600), (7936, 992), (7936, 4704)]


def face_center(x, y):
    dx, dy = HALL_CENTER[0] - x, HALL_CENTER[1] - y
    if abs(dx) < 1 and abs(dy) < 1:
        return 0.0
    return round(math.degrees(math.atan2(dy, dx)), 1)


FFA = [("SP_FFA_%d" % (i + 1), x, y, face_center(x, y)) for i, (x, y) in enumerate(FFA_POINTS)]


def set_override(text, name, value):
    """Значение настройки в PlayerOptionData (то, что видно в «Сведениях»)."""
    pattern = r'\(PropertyName="%s"(,PropertyData="[^"]*")?\)' % re.escape(name)
    text, count = re.subn(pattern, '(PropertyName="%s",PropertyData="%s")' % (name, value), text)
    assert count == 1, name
    return text


def make_spawner(template, serial, label, x, y, yaw):
    actor_name = "BP_Creative_Player_Spawner_Prop_C_UAID_B0D1CA4A5000000000_%02d" % serial
    text = template.replace(TEMPLATE_NAME, actor_name)
    text = re.sub(r"RelativeLocation=\(X=[^)]*\)",
                  "RelativeLocation=(X=%.6f,Y=%.6f,Z=%.6f)" % (x, y, FLOOR_Z), text)
    text = re.sub(r"RelativeRotation=\(Pitch=[^)]*\)",
                  "RelativeRotation=(Pitch=0.000000,Yaw=%.6f,Roll=0.000000)" % yaw, text)
    text = re.sub(r"\n\s*SavedActorGuid=\w+", "", text)  # UEFN выдаст свой
    text = set_override(text, "LabelOverride", label)
    text = re.sub(r'LabelOverride="[^"]*"', 'LabelOverride="%s"' % label, text)
    text = re.sub(r'ActorLabel="[^"]*"', 'ActorLabel="%s"' % label, text)
    return text


def write(name, template, spawns, first_serial):
    actors = [make_spawner(template, first_serial + i, *s) for i, s in enumerate(spawns)]
    body = "Begin Map\n   Begin Level\n%s\n   End Level\nBegin Surface\nEnd Surface\nEnd Map\n" % "\n".join(actors)
    (PASTE / name).write_text(body, encoding="utf-8")
    print("paste/%s: %d спавнов" % (name, len(actors)))


def main():
    template = TEMPLATE.read_text(encoding="utf-8").rstrip("\n")
    write("06_spawns_lobby.txt", template, LOBBY, 1)
    write("07_spawns_teams.txt", template, TEAMS, 21)
    write("08_spawns_ffa.txt", template, FFA, 41)


if __name__ == "__main__":
    main()
