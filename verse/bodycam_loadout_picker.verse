# BODYCAM для Fortnite: меню выбора снаряжения.
# Открывается в подготовке раунда или на экране «НЕТ СИГНАЛА» между возрождениями.
# Выбор сохраняется: если ничего не нажать, остаётся прежний набор.

using { /Fortnite.com/UI }
using { /UnrealEngine.com/Temporary/UI }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /Verse.org/Simulation }

# Verse не умеет замыкания, поэтому каждая кнопка хранит свой индекс в отдельном объекте.
bodycam_loadout_button := class:
    Picker : bodycam_loadout_picker
    Index : int

    OnClick(Message:widget_message):void =
        Picker.Choose(Index)

bodycam_loadout_picker := class:
    Player : player
    Names : []string

    var Selected : int = 0
    var IsOpen : logic = false
    var MaybeRoot : ?canvas = false

    TitleText : text_block = text_block{DefaultTextColor := BodycamWhite}

    HasOptions()<transacts>:logic =
        if (Names.Length > 0) then true else false

    SelectedName():string =
        if (Name := Names[Selected]) then Name else ""

    Open(Title:string):void =
        if (not IsOpen?, HasOptions()?, PlayerUI := GetPlayerUI[Player]):
            TitleText.SetText(BodycamText(Title))
            var Slots : []stack_box_slot = array:
                stack_box_slot:
                    Widget := TitleText
                    HorizontalAlignment := horizontal_alignment.Center
                    Padding := margin{Bottom := 12.0}
            for (Index -> Name : Names):
                Marker := if (Index = Selected) then "›  " else ""
                Button := button_loud{DefaultText := BodycamText("{Marker}{Index + 1}. {Name}")}
                Handler := bodycam_loadout_button{Picker := Self, Index := Index}
                Button.OnClick().Subscribe(Handler.OnClick)
                ButtonSlot := stack_box_slot:
                    Widget := Button
                    HorizontalAlignment := horizontal_alignment.Fill
                    Padding := margin{Top := 4.0}
                set Slots = Slots + array{ButtonSlot}

            Box := stack_box{Orientation := orientation.Vertical, Slots := Slots}
            Root := canvas{Slots := array{AnchoredSlot(Box, 0.5, 0.5, 0.0, 60.0)}}
            # Курсор нужен, чтобы нажимать кнопки. Во время подготовки и смерти обзор всё равно не нужен.
            PlayerUI.AddWidget(Root, player_ui_slot{InputMode := ui_input_mode.All})
            set MaybeRoot = option{Root}
            set IsOpen = true

    Choose(Index:int):void =
        set Selected = Index
        Close()

    Close():void =
        if (IsOpen?):
            set IsOpen = false
            if (PlayerUI := GetPlayerUI[Player], Root := MaybeRoot?):
                PlayerUI.RemoveWidget(Root)
            set MaybeRoot = false
