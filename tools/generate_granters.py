#!/usr/bin/env python3
"""Устройства выдачи предметов для арсенала BODYCAM (вставка в UEFN через Ctrl+V).

Берёт образец одного устройства, скопированного из UEFN (tools/templates/item_granter.t3d),
и собирает paste/05_item_granters.txt: 15 устройств с названиями из docs/START_HERE.md, рядом
в здании брифинга. Предмет остаётся только в G_AR (как в образце), в остальных его нужно выбрать.

    python3 tools/generate_granters.py
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "tools" / "templates" / "item_granter.t3d"
OUT = ROOT / "paste" / "05_item_granters.txt"

TEMPLATE_NAME = "Device_ItemGranter_V2_C_UAID_40C73C33DC6C100C03_2088964341"
LIGHT_HEIGHT = 85.664684  # точка подсветки над устройством, из образца

# (название, основное оружие?) — основное очищает инвентарь и сразу в руки,
# пистолеты и гранаты добавляются после него.
GRANTERS = [
    ("G_AR", True),
    ("G_AR_Suppressed", True),
    ("G_AR_Scoped", True),
    ("G_AR_Thermal", True),
    ("G_SMG", True),
    ("G_SMG_Suppressed", True),
    ("G_Pump", True),
    ("G_DMR", True),
    ("G_Sniper_Suppressed", True),
    ("G_Pistol", False),
    ("G_Pistol_Suppressed", False),
    ("G_Revolver", False),
    ("G_HandCannon", False),
    ("G_Smoke", False),
    ("G_Grenade", False),
]

# Вдоль северной стены брифинга (LOBBY_RECT в generate_paste.py: x 9000…11000, y 1500…2900).
START_X, STEP_X, ROW_Y, FLOOR_Z = 9150.0, 120.0, 2780.0, 0.0


def set_override(text, name, value):
    """Значение настройки в PlayerOptionData (то, что видно в «Сведениях»)."""
    pattern = r'\(PropertyName="%s"(,PropertyData="[^"]*")?\)' % re.escape(name)
    replacement = '(PropertyName="%s",PropertyData="%s")' % (name, value)
    text, count = re.subn(pattern, replacement, text)
    assert count == 1, name
    return text


def make_granter(template, index, label, primary):
    actor_name = "Device_ItemGranter_V2_C_UAID_B0D1CA4A0000000000_%02d" % (index + 1)
    text = template.replace(TEMPLATE_NAME, actor_name)
    x, y = START_X + STEP_X * index, ROW_Y

    text = re.sub(r"RelativeLocation=\(X=[^)]*\)",
                  "RelativeLocation=(X=%.6f,Y=%.6f,Z=%.6f)" % (x, y, FLOOR_Z), text)
    text = re.sub(r"Position=\(X=[^)]*\)",
                  "Position=(X=%.6f,Y=%.6f,Z=%.6f)" % (x, y, FLOOR_Z + LIGHT_HEIGHT), text)

    # Уникальные идентификаторы UEFN выдаст сам.
    text = re.sub(r"\n\s*PersistenceID=\w+", "", text)
    text = re.sub(r"\n\s*SavedActorGuid=\w+", "", text)

    text = set_override(text, "LabelOverride", label)
    text = text.replace('LabelOverride="G_AR"', 'LabelOverride="%s"' % label)
    text = text.replace('ActorLabel="G_AR"', 'ActorLabel="%s"' % label)

    text = set_override(text, "bEquipGrantedItem", "True" if primary else "False")
    if primary:
        text = text.replace("         InitialWeaponAmmo=3\n",
                            "         InitialWeaponAmmo=3\n         bEquipGrantedItem=True\n")
    else:
        # Вариант «не очищать» в образце не встречался: убираем настройку, остаётся значение по умолчанию.
        text = re.sub(r'\(PropertyName="OnGrantAction",PropertyData="[^"]*"\),', "", text)

    if label != "G_AR":
        text = re.sub(r"\n\s*ItemListData\(0\)=\([^\n]*\)", "", text)
    return text


def main():
    template = TEMPLATE.read_text(encoding="utf-8").rstrip("\n")
    actors = [make_granter(template, i, label, primary) for i, (label, primary) in enumerate(GRANTERS)]
    body = "Begin Map\n   Begin Level\n%s\n   End Level\nBegin Surface\nEnd Surface\nEnd Map\n" % "\n".join(actors)
    OUT.write_text(body, encoding="utf-8")
    print("%s: %d устройств" % (OUT.relative_to(ROOT), len(actors)))


if __name__ == "__main__":
    main()
