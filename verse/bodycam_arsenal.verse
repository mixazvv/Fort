# BODYCAM для Fortnite: арсенал и кастомизация оружия.
#
# Как в Bodycam, игрок собирает снаряжение: платформа основного оружия, прицел, дульное устройство,
# пистолет и снаряжение. В Fortnite нельзя вешать модули на ствол, поэтому каждая комбинация
# «платформа + прицел + дуло» — это отдельный предмет Fortnite в своём Item Granter
# (например, «винтовка + глушитель» = Suppressed Assault Rifle). Меню собирает их как обвесы.
#
# Выбор игрока хранится всю игровую сессию, в том числе между раундами.

using { /Fortnite.com/Devices }
using { /Fortnite.com/UI }
using { /UnrealEngine.com/Temporary/UI }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /Verse.org/Simulation }

# Один вариант основного оружия.
bodycam_weapon_variant := class<concrete>:
    # Платформа: одинаковое название объединяет варианты в одну строку меню.
    @editable
    Platform : string = "ШТУРМОВАЯ ВИНТОВКА"

    @editable
    Optic : string = "МЕХАНИКА"

    @editable
    Muzzle : string = "НЕТ"

    # Выдаёт это оружие. Включите в нём очистку инвентаря при выдаче.
    @editable
    Granter : item_granter_device = item_granter_device{}

# Пистолет или снаряжение.
bodycam_gear_option := class<concrete>:
    @editable
    Name : string = ""

    # Не очищает инвентарь при выдаче: выдаётся после основного оружия.
    @editable
    Granter : item_granter_device = item_granter_device{}

# Выбор одного игрока.
bodycam_loadout := class:
    var Platform : int = 0
    var Optic : string = ""
    var Muzzle : string = ""
    var Pistol : int = 0
    var Gear : int = 0

var BodycamLoadouts : weak_map(session, [player]bodycam_loadout) = map{}

HasString(Items:[]string, Item:string)<transacts>:logic =
    var Found : logic = false
    for (X : Items, X = Item):
        set Found = true
    Found

CycleIndex(Current:int, Count:int, Step:int):int =
    if (Count > 0, Result := Mod[Current + Step + Count, Count]) then Result else 0

CycleString(Items:[]string, Current:string, Step:int):string =
    var Index : int = 0
    for (I -> X : Items, X = Current):
        set Index = I
    NewIndex := CycleIndex(Index, Items.Length, Step)
    if (Item := Items[NewIndex]) then Item else Current

# Действия кнопок меню: чётные — «назад», нечётные — «вперёд».
ArsenalPlatformPrev : int = 0
ArsenalPlatformNext : int = 1
ArsenalOpticPrev : int = 2
ArsenalOpticNext : int = 3
ArsenalMuzzlePrev : int = 4
ArsenalMuzzleNext : int = 5
ArsenalPistolPrev : int = 6
ArsenalPistolNext : int = 7
ArsenalGearPrev : int = 8
ArsenalGearNext : int = 9
ArsenalReady : int = 10
ArsenalClose : int = 11

bodycam_arsenal_device := class(creative_device):

    # Варианты основного оружия. Пример в docs/START_HERE.md.
    @editable
    Variants : []bodycam_weapon_variant = array{}

    @editable
    Pistols : []bodycam_gear_option = array{}

    # Гранаты, дым и т.п. Первым пунктом удобно сделать «НЕТ» с пустым Item Granter.
    @editable
    Gear : []bodycam_gear_option = array{}

    var Menus : [player]bodycam_arsenal_menu = map{}
    var Ready : [player]logic = map{}

    # ---------- Списки для меню ----------

    Platforms()<transacts>:[]string =
        var Result : []string = array{}
        for (V : Variants, not HasString(Result, V.Platform)?):
            set Result = Result + array{V.Platform}
        Result

    OpticsFor(Platform:string)<transacts>:[]string =
        var Result : []string = array{}
        for (V : Variants, V.Platform = Platform, not HasString(Result, V.Optic)?):
            set Result = Result + array{V.Optic}
        Result

    MuzzlesFor(Platform:string, Optic:string)<transacts>:[]string =
        var Result : []string = array{}
        for (V : Variants, V.Platform = Platform, V.Optic = Optic, not HasString(Result, V.Muzzle)?):
            set Result = Result + array{V.Muzzle}
        Result

    PlatformName(L:bodycam_loadout)<transacts>:string =
        List := Platforms()
        if (Name := List[L.Platform]) then Name else ""

    # Ближайший вариант к выбору: совпадение прицела важнее совпадения дула.
    ResolveVariant(L:bodycam_loadout)<transacts>:?bodycam_weapon_variant =
        Platform := PlatformName(L)
        var Best : ?bodycam_weapon_variant = false
        var BestScore : int = -1
        for (V : Variants, V.Platform = Platform):
            OpticScore := if (V.Optic = L.Optic) then 2 else 0
            MuzzleScore := if (V.Muzzle = L.Muzzle) then 1 else 0
            if (OpticScore + MuzzleScore > BestScore):
                set BestScore = OpticScore + MuzzleScore
                set Best = option{V}
        Best

    # ---------- Выбор игрока ----------

    GetLoadout(P:player):bodycam_loadout =
        var All : [player]bodycam_loadout = map{}
        if (Existing := BodycamLoadouts[GetSession()]):
            set All = Existing
        if (Found := All[P]):
            Found
        else:
            Created := bodycam_loadout{}
            if (set All[P] = Created) {}
            if (set BodycamLoadouts[GetSession()] = All) {}
            Normalize(Created)
            Created

    # Подгоняет прицел и дуло под реально существующий вариант.
    Normalize(L:bodycam_loadout):void =
        if (L.Platform >= Platforms().Length):
            set L.Platform = 0
        MaybeVariant := ResolveVariant(L)
        if (V := MaybeVariant?):
            set L.Optic = V.Optic
            set L.Muzzle = V.Muzzle
        if (L.Pistol >= Pistols.Length):
            set L.Pistol = 0
        if (L.Gear >= Gear.Length):
            set L.Gear = 0

    Change(P:player, Action:int):void =
        L := GetLoadout(P)
        Step := if (Mod[Action, 2] = 0) then -1 else 1
        Kind := if (K := Quotient[Action, 2]) then K else -1
        if (Kind = 0):
            set L.Platform = CycleIndex(L.Platform, Platforms().Length, Step)
            set L.Optic = ""
            set L.Muzzle = ""
        else if (Kind = 1):
            set L.Optic = CycleString(OpticsFor(PlatformName(L)), L.Optic, Step)
            set L.Muzzle = ""
        else if (Kind = 2):
            set L.Muzzle = CycleString(MuzzlesFor(PlatformName(L), L.Optic), L.Muzzle, Step)
        else if (Kind = 3):
            set L.Pistol = CycleIndex(L.Pistol, Pistols.Length, Step)
        else if (Kind = 4):
            set L.Gear = CycleIndex(L.Gear, Gear.Length, Step)
        Normalize(L)

    # Выдать собранное снаряжение: основное оружие (очищает инвентарь), затем пистолет и снаряжение.
    Grant(P:player):void =
        L := GetLoadout(P)
        MaybeVariant := ResolveVariant(L)
        if (V := MaybeVariant?):
            V.Granter.GrantItem(P)
        if (Pistol := Pistols[L.Pistol]):
            Pistol.Granter.GrantItem(P)
        if (Item := Gear[L.Gear]):
            Item.Granter.GrantItem(P)

    HasLoadoutOptions()<transacts>:logic =
        if (Variants.Length + Pistols.Length + Gear.Length > 0) then true else false

    # ---------- Готовность в лобби ----------

    IsReady(P:player)<transacts>:logic =
        if (Value := Ready[P]) then Value else false

    ToggleReady(P:player):void =
        NewValue := if (IsReady(P)?) then false else true
        if (set Ready[P] = NewValue) {}

    ResetReady():void =
        set Ready = map{}

    CountReady(Players:[]player)<transacts>:int =
        var Count : int = 0
        for (P : Players, IsReady(P)?):
            set Count += 1
        Count

    # ---------- Меню ----------

    GetMenu(P:player):bodycam_arsenal_menu =
        if (Existing := Menus[P]):
            Existing
        else:
            Created := bodycam_arsenal_menu{Arsenal := Self, Player := P}
            if (set Menus[P] = Created) {}
            Created

    OpenMenu(P:player, Title:string, ShowReady:logic):void =
        GetMenu(P).Open(Title, ShowReady)

    CloseMenu(P:player):void =
        if (Menu := Menus[P]):
            Menu.Close()

    CloseAll():void =
        for (P -> Menu : Menus):
            Menu.Close()

    SetStatusAll(Text:string):void =
        for (P -> Menu : Menus):
            Menu.SetStatus(Text)

    Handle(P:player, Action:int):void =
        if (Action = ArsenalReady):
            ToggleReady(P)
        else if (Action <> ArsenalClose):
            Change(P, Action)

# Кнопка меню. Verse не умеет замыкания, поэтому действие хранится в отдельном объекте.
bodycam_arsenal_action := class:
    Menu : bodycam_arsenal_menu
    Action : int

    OnClick(Message:widget_message):void =
        Menu.OnAction(Action)

bodycam_arsenal_menu := class:
    Arsenal : bodycam_arsenal_device
    Player : player

    var IsOpen : logic = false
    var MaybeRoot : ?canvas = false

    TitleText : text_block = text_block{DefaultTextColor := BodycamWhite}
    StatusText : text_block = text_block{DefaultTextColor := BodycamAmber}
    PlatformText : text_block = text_block{DefaultTextColor := BodycamWhite}
    OpticText : text_block = text_block{DefaultTextColor := BodycamWhite}
    MuzzleText : text_block = text_block{DefaultTextColor := BodycamWhite}
    PistolText : text_block = text_block{DefaultTextColor := BodycamWhite}
    GearText : text_block = text_block{DefaultTextColor := BodycamWhite}
    Backdrop : color_block = color_block{DefaultColor := BodycamBlack, DefaultOpacity := 0.6}
    ReadyButton : button_loud = button_loud{}
    CloseButton : button_quiet = button_quiet{}

    Open(Title:string, ShowReady:logic):void =
        if (not IsOpen?, PlayerUI := GetPlayerUI[Player]):
            Root := GetRoot()
            TitleText.SetText(BodycamText(Title))
            ReadyButton.SetVisibility(if (ShowReady?) then widget_visibility.Visible else widget_visibility.Collapsed)
            Refresh()
            # Курсор нужен, чтобы нажимать кнопки.
            PlayerUI.AddWidget(Root, player_ui_slot{InputMode := ui_input_mode.All})
            set IsOpen = true

    Close():void =
        if (IsOpen?):
            set IsOpen = false
            if (PlayerUI := GetPlayerUI[Player], Root := MaybeRoot?):
                PlayerUI.RemoveWidget(Root)

    SetStatus(Text:string):void =
        StatusText.SetText(BodycamText(Text))

    OnAction(Action:int):void =
        Arsenal.Handle(Player, Action)
        if (Action = ArsenalClose):
            Close()
        else:
            Refresh()

    Refresh():void =
        L := Arsenal.GetLoadout(Player)
        Dash := "—"
        Platform := Arsenal.PlatformName(L)
        PlatformText.SetText(BodycamText(if (Platform <> "") then Platform else Dash))
        OpticText.SetText(BodycamText(if (L.Optic <> "") then L.Optic else Dash))
        MuzzleText.SetText(BodycamText(if (L.Muzzle <> "") then L.Muzzle else Dash))
        PistolText.SetText(BodycamText(if (Pistol := Arsenal.Pistols[L.Pistol]) then Pistol.Name else Dash))
        GearText.SetText(BodycamText(if (Item := Arsenal.Gear[L.Gear]) then Item.Name else Dash))
        ReadyButton.SetText(BodycamText(if (Arsenal.IsReady(Player)?) then "✔  ГОТОВ" else "ГОТОВ"))

    MakeButton(Label:string, Action:int):button_quiet =
        Button := button_quiet{DefaultText := BodycamText(Label)}
        Handler := bodycam_arsenal_action{Menu := Self, Action := Action}
        Button.OnClick().Subscribe(Handler.OnClick)
        Button

    Row(Label:string, Value:text_block, Prev:int, Next:int):stack_box_slot =
        PrevButton := MakeButton("‹", Prev)
        NextButton := MakeButton("›", Next)
        LabelText := text_block{DefaultText := BodycamText(Label), DefaultTextColor := BodycamAmber}
        Line := stack_box:
            Orientation := orientation.Horizontal
            Slots := array:
                stack_box_slot:
                    Widget := LabelText
                    VerticalAlignment := vertical_alignment.Center
                    Padding := margin{Right := 18.0}
                stack_box_slot:
                    Widget := PrevButton
                stack_box_slot:
                    Widget := Value
                    VerticalAlignment := vertical_alignment.Center
                    Padding := margin{Left := 14.0, Right := 14.0}
                stack_box_slot:
                    Widget := NextButton
        stack_box_slot:
            Widget := Line
            HorizontalAlignment := horizontal_alignment.Left
            Padding := margin{Top := 6.0}

    GetRoot():canvas =
        if (Existing := MaybeRoot?):
            Existing
        else:
            ReadyButton.SetText(BodycamText("ГОТОВ"))
            ReadyHandler := bodycam_arsenal_action{Menu := Self, Action := ArsenalReady}
            ReadyButton.OnClick().Subscribe(ReadyHandler.OnClick)
            CloseButton.SetText(BodycamText("ЗАКРЫТЬ"))
            CloseHandler := bodycam_arsenal_action{Menu := Self, Action := ArsenalClose}
            CloseButton.OnClick().Subscribe(CloseHandler.OnClick)

            var Slots : []stack_box_slot = array:
                stack_box_slot:
                    Widget := TitleText
                    HorizontalAlignment := horizontal_alignment.Left
                stack_box_slot:
                    Widget := StatusText
                    HorizontalAlignment := horizontal_alignment.Left
                    Padding := margin{Bottom := 14.0}
            if (Arsenal.HasLoadoutOptions()?):
                set Slots = Slots + array:
                    Row("ОСНОВНОЕ", PlatformText, ArsenalPlatformPrev, ArsenalPlatformNext)
                    Row("ПРИЦЕЛ", OpticText, ArsenalOpticPrev, ArsenalOpticNext)
                    Row("ДУЛО", MuzzleText, ArsenalMuzzlePrev, ArsenalMuzzleNext)
                    Row("ПИСТОЛЕТ", PistolText, ArsenalPistolPrev, ArsenalPistolNext)
                    Row("СНАРЯЖЕНИЕ", GearText, ArsenalGearPrev, ArsenalGearNext)
            set Slots = Slots + array:
                stack_box_slot:
                    Widget := ReadyButton
                    HorizontalAlignment := horizontal_alignment.Fill
                    Padding := margin{Top := 20.0}
                stack_box_slot:
                    Widget := CloseButton
                    HorizontalAlignment := horizontal_alignment.Fill
                    Padding := margin{Top := 6.0}

            Panel := stack_box{Orientation := orientation.Vertical, Slots := Slots}
            Root := canvas:
                Slots := array:
                    FullScreenSlot(Backdrop)
                    AnchoredSlot(Panel, 0.5, 0.5, 0.0, 0.0)
            set MaybeRoot = option{Root}
            Root
