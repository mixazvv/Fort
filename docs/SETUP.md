# Сборка режима BODYCAM в UEFN

Названия настроек в UEFN иногда меняются от версии к версии. Если пункт называется иначе, ищите ближайший по смыслу.

Режимов три, и у каждого свои Island Settings: в «Раундах» одна жизнь, в остальных возрождение. Поэтому каждый режим собирается как **отдельный остров**: сделайте карту один раз, затем скопируйте проект (или папку уровня) и поменяйте настройки и менеджер.

| Режим | Verse-устройство | Разделы |
|---|---|---|
| Раунды 5 на 5 | `bodycam_rounds_manager` | 1–6 |
| Deathmatch | `bodycam_deathmatch_manager` | 1, 4–5 и 7 |
| Гонка вооружений | `bodycam_gungame_manager` | 1, 4–5 и 7 |

Карта: [MAP.md](MAP.md).

## 1. Проект и код

1. Откройте UEFN и создайте проект из шаблона **Blank** (или любого пустого острова).
2. Скопируйте все файлы из папки `verse/` этого репозитория в Verse-папку проекта. Её видно через **Verse Explorer**: правый клик по проекту → *Open in File Explorer*. Обычно путь такой: `Documents/Fortnite Projects/<Проект>/Plugins/<Проект>/Content/`.
3. **Verse → Build Verse Code** (Ctrl+Shift+B). Должно собраться без ошибок. Если нет, смотрите раздел «Если не компилируется».
4. В Content Browser найдите менеджер нужного режима (`bodycam_rounds_manager`, `bodycam_deathmatch_manager` или `bodycam_gungame_manager`) и перетащите его на уровень. Ставьте только один менеджер на остров. `bodycam_respawn_mode` — общая основа, на уровень её не ставят.

## 2. Island Settings (Раунды)

| Раздел | Настройка | Значение |
|---|---|---|
| Игроки | Max Players | 10 |
| Команды | Team Count | 2 |
| | Team Size | 5 |
| | Friendly Fire / Team Damage | On (рекомендуется) |
| Раунды | Total Rounds | 15 (с запасом, матч завершит Verse) |
| Спавн | Spawn Limit | 1 (одна жизнь за раунд) |
| | Eliminated players | Spectate teammates |
| Здоровье | Max Health / Starting Health | 100 (Verse выставит 45) |
| | Max Shield / Starting Shield | 0 |
| | Health / Shield Regeneration | Off |
| | Fall Damage | On |
| Строительство | Allow Building | None |
| | Environment Damage | Off |
| Предметы | Infinite Ammo | Off |
| | Drop items on elimination | Off |
| | Starting inventory | пусто (выдаёт Verse) |
| Интерфейс | Show Names / Nameplates | Off |
| Прочее | Time of Day | ночь (около 02:00) |

## 3. Устройства (Раунды)

Расставьте и свяжите с `bodycam_rounds_manager` (панель Details → поля @editable):

| Устройство | Настройки | Поле в Verse |
|---|---|---|
| **Round Settings** | по умолчанию | `RoundSettings` |
| **End Game** | End: Game, Winner: Activating Team | `EndGame` |
| **Item Granter** ×N (по одному на набор) | Grant: Weapon + Pistol, On Grant: Clear Inventory, Equip: First Item, боезапас 2–3 магазина | `LoadoutGranters` |
| **Movement Modulator** | Movement Multiplier 0.85, Effect Duration: Infinite | `MovementModulators` |
| **Audio Player** — сердцебиение | Heartbeat, Play to: Registered/Instigator, Looping off | `InjuredSounds` |
| **Audio Player** — одышка | heavy breathing | `BreathingSounds` |
| **Audio Player** — рация | короткий хрип / щелчок рации | `RadioSounds` |
| **Audio Player** — старт | диспетчер, далёкая сирена (для всех) | `RoundStartSounds` |

Без связи с Verse:

- **Player Spawner**: по 5 на команду, на противоположных концах карты, Team 1 и Team 2.
- **First Person Camera** (Camera — First Person): Add Players on Start = On, все команды.
- **HUD Controller**: выключите всё (Health, Shield, Minimap, Elimination feed, Team info, Round info, Quick bar по желанию, Crosshair по желанию; без прицела будет хардкорнее). Оверлей Verse при этом останется на экране.
- **Post Process Volume**: Infinite Extent (Unbound) = On, настройки ниже.
- **Exponential Height Fog**: Volumetric Fog On, Density около 0.03, холодный голубоватый цвет.

Звуки нужно импортировать свои (лицензионные или бесплатные: freesound.org с подходящей лицензией и т.п.).

## 4. Пост-обработка

Это главный источник «бодикамовости». Значения стартовые, подкручивайте на своей карте.

| Группа | Параметр | Значение |
|---|---|---|
| Lens → Bloom | Intensity | 1.5 |
| | Threshold | 0.6 |
| Lens → Chromatic Aberration | Intensity | 1.2 |
| | Start Offset | 0.25 |
| Lens → Image Effects | Vignette Intensity | 0.9 |
| | Grain Intensity | 0.45 |
| | Grain Jitter | 0.6 |
| Lens → Exposure | Metering Mode | Auto Exposure Histogram |
| | Speed Up | 1.0 (медленно привыкает к свету) |
| | Speed Down | 3.0 |
| | Min/Max EV100 | -1 / 8 |
| Lens → Lens Flares | Intensity | 0.3 |
| Color Grading → Global | Saturation | 0.7 |
| | Contrast | 1.15 |
| | Gamma | 1.05 |
| Color Grading → Shadows | Saturation | 0.6, оттенок в сине-зелёный |
| Color Grading → Highlights | Gain | слегка в жёлтый (натриевые лампы) |
| White Balance | Temp | 7000 (холодная картинка) |
| Rendering → Motion Blur | Amount | 0.8 |
| | Max | 8 |
| Film → Toe/Shoulder | Toe 0.6, Shoulder 0.3 | грязные чёрные |
| Camera | Field of View (если доступно в First Person Camera) | 100–110 |

### «Рыбий глаз» через пост-процесс материал

Если в вашей версии UEFN доступны пост-процесс материалы (Post Process Materials в Post Process Volume), создайте материал:

- **Material Domain:** Post Process, **Blendable Location:** Before Tonemapping.

Граф узлов (бочкообразная дисторсия):

```
UV      = ScreenPosition (ViewportUV)
C       = UV - (0.5, 0.5)
R2      = Dot(C, C)
K       = ScalarParameter "Distortion" = 0.25
UVd     = C * (1 + K * R2) * ScalarParameter "Zoom"(0.92) + (0.5, 0.5)
Color   = SceneTexture:PostProcessInput0 (UV = UVd)
Emissive = Color
```

Для более «дешёвой» камеры возьмите три выборки SceneTexture с K = 0.24 / 0.25 / 0.26 и соберите из них R, G и B. Это даст дополнительную цветную кайму по краям.

Добавьте материал в Post Process Volume → Rendering Features → Post Process Materials. Если пост-процесс материалы недоступны, остаются виньетка, аберрация и широкий FOV. Этого хватает на 70% эффекта.

## 5. Свет и уровень

- Lumen включён, Directional Light (луна) слабый: интенсивность 0.1–0.3, холодный цвет.
- Основной свет даёт малое число точечных источников: лампы дневного света в помещениях, натриевые фонари на улице.
- 2–3 мерцающие лампы: Light + Timer/Trigger или Verse-цикл с Enable/Disable.
- В тёмных углах реально темно, без заполняющего света. Зерно сделает их шумными.
- Сделайте «грязь»: декали, мусор, коробки, кабели. Реалистичные ассеты можно брать с Fab, если позволяет бюджет памяти острова.

## 6. Проверка

1. **Launch Session**, затем запустите сессию с 2+ игроками (можно с ботами или вторым аккаунтом).
2. Проверьте:
   - [ ] В начале раунда видны «РАУНД 1» и отсчёт подготовки, игроки стоят на месте.
   - [ ] После отсчёта игроки двигаются, выдано оружие из одного из наборов.
   - [ ] Мигает REC, идут часы, отображается позывной.
   - [ ] Попадание даёт вспышку. После 2 попаданий из AR игрок выбывает.
   - [ ] Ниже 50% HP появляется красная виньетка и звучит сердцебиение.
   - [ ] Выбывание: помехи, затем «НЕТ СИГНАЛА». Союзники видят «РАЦИЯ › …: нет связи».
   - [ ] После гибели всей команды показывается «РАУНД ЗА …», счёт растёт и начинается следующий раунд.
   - [ ] Счёт сохраняется между раундами, при 5 победах матч заканчивается.
   - [ ] По истечении 3:00 раунд достаётся команде, у которой больше живых.

## 7. Deathmatch и Гонка вооружений

### Island Settings (отличия от «Раундов»)

| Настройка | Значение |
|---|---|
| Max Players | 12 |
| Teams | Free For All (каждый сам за себя) |
| Total Rounds | 1 |
| Spawn Limit | без ограничения (возрождение включено) |
| Respawn Time | 3 с (больше, чем `SignalLostSeconds` = 2,5 с) |
| Spawn Location | Player Spawners |
| Max Health / Shield, регенерация, строительство | как в «Раундах» |

### Устройства

| Устройство | Настройки | Поле в Verse |
|---|---|---|
| **End Game** | End: Game, Winner: Activating Player | `EndGame` |
| **Player Spawner** ×12 | Team: Any, координаты в [MAP.md](MAP.md) | `Spawners` (добавьте **все**) |
| **Movement Modulator** | как в «Раундах» | `MovementModulators` |
| **Audio Player** — сердцебиение / одышка | как в «Раундах» | `InjuredSounds`, `BreathingSounds` |
| **Audio Player** — подтверждение | короткий щелчок рации | `KillConfirmSounds` |

First Person Camera, HUD Controller, Post Process Volume и туман такие же, как в разделе 3.

### Deathmatch (`bodycam_deathmatch_manager`)

- `LoadoutGranters`: 3–5 Item Granter с наборами (например, «винтовка + пистолет», «ПП + пистолет», «дробовик + пистолет»). В каждом включите очистку инвентаря при выдаче. Набор выдаётся случайно при каждом возрождении.
- `KillsToWin` = 25, `MatchSeconds` = 600.
- Смерть без убийцы (падение) отнимает 1 очко.

### Гонка вооружений (`bodycam_gungame_manager`)

- `WeaponTiers`: Item Granter по одному на ступень. Каждый выдаёт **одно** оружие с запасом патронов и очищает инвентарь. Порядок от сильного к слабому, пример на 12 ступеней:

  | # | Оружие | | # | Оружие |
  |---|---|---|---|---|
  | 1 | Штурмовая винтовка (легендарная) | | 7 | Тактический дробовик |
  | 2 | Штурмовая винтовка (обычная) | | 8 | Револьвер |
  | 3 | Пулемёт | | 9 | Пистолет с глушителем |
  | 4 | Пистолет-пулемёт | | 10 | Пистолет |
  | 5 | Марксманская винтовка | | 11 | Снайперская винтовка с продольным затвором |
  | 6 | Помповый дробовик | | 12 | Пистолет (обычный) |

  Пистолет на последней ступени работает как «нож» из классического Gun Game: последнее и самое трудное убийство.
- `TierNames`: названия для экрана в том же порядке («ШТУРМОВАЯ ВИНТОВКА», «ПП» и т.д.).
- `DemoteOnSuicide` = true: падение откатывает на ступень назад.
- `MatchSeconds` = 600. Если время вышло, побеждает тот, кто продвинулся дальше всех.

### Проверка

- [ ] После возрождения снова идёт запись (● REC), «НЕТ СИГНАЛА» пропадает, здоровье 45.
- [ ] Убийца видит «РАЦИЯ › UNIT-04: цель нейтрализована».
- [ ] Deathmatch: счётчик «УБИЙСТВ n/25» растёт, при 25 появляется «КОНЕЦ СМЕНЫ» и матч заканчивается.
- [ ] Гонка: после убийства оружие меняется сразу, по центру появляется название нового. Убийство на последней ступени заканчивает матч.

## 8. Если не компилируется

Код написан под текущий API Verse, но собрать его в UEFN из этого окружения не получилось. Вероятные расхождения:

- **`round_settings_device.EndRound`**: если метода нет, используйте второе `end_game_device` в режиме *End: Round* и вызывайте `.Activate(P)`.
- **`audio_player_device.Play(Agent)`**: если перегрузки нет, используйте `Play()` и настройте устройство так, чтобы звук был позиционным у игрока.
- **`SprintedEvent`**: если у `fort_character` нет этого события, удалите подписку в `bodycam_agent.verse`. Одышка просто пропадёт.
- **Абстрактный класс** `bodycam_respawn_mode`: если UEFN не принимает `class<abstract>` от `creative_device`, уберите `<abstract>` и дайте методам `GrantForPlayer`, `OnKill` и остальным пустые тела (`= {}`, а для возвращающих значение `= false` или `= ""`).
- **`GetSession()`**: если не находится, проверьте `using { /Verse.org/Simulation }`.
- Ошибки про эффекты (`<transacts>`, `<decides>`): обычно лечатся оборачиванием вызова в `if (...) {}`.

Пришлите текст ошибки, и я поправлю код.
