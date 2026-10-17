# BODYCAM для Fortnite: экранный оверлей нагрудной камеры для одного игрока.
# Мигающий REC, таймкод, позывной, параметры объектива, сообщения рации,
# вспышки при попадании, красная виньетка ранения и экран «НЕТ СИГНАЛА».

using { /Fortnite.com/UI }
using { /UnrealEngine.com/Temporary/UI }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /Verse.org/Simulation }
using { /Verse.org/Random }

# Виджет, растянутый на весь экран.
FullScreenSlot(W:widget):canvas_slot =
    canvas_slot:
        Anchors := anchors{Minimum := vector2{X := 0.0, Y := 0.0}, Maximum := vector2{X := 1.0, Y := 1.0}}
        Offsets := margin{}
        Alignment := vector2{X := 0.0, Y := 0.0}
        SizeToContent := false
        Widget := W

# Виджет, привязанный к точке экрана (0..1) со сдвигом в пикселях.
# Выравнивание совпадает с якорем, поэтому правый угол отсчитывается от правого края.
AnchoredSlot(W:widget, AnchorX:float, AnchorY:float, OffsetX:float, OffsetY:float):canvas_slot =
    canvas_slot:
        Anchors := anchors{Minimum := vector2{X := AnchorX, Y := AnchorY}, Maximum := vector2{X := AnchorX, Y := AnchorY}}
        Offsets := margin{Left := OffsetX, Top := OffsetY}
        Alignment := vector2{X := AnchorX, Y := AnchorY}
        SizeToContent := true
        Widget := W

bodycam_overlay := class:
    Player : player
    Callsign : string
    CameraModel : string
    DateStamp : string

    var ClockSeconds : int = 0
    var CenterToken : int = 0
    var RadioToken : int = 0
    var IsRecording : logic = true
    var MaybeRoot : ?canvas = false

    RecText : text_block = text_block{DefaultTextColor := BodycamRed}
    UnitText : text_block = text_block{DefaultTextColor := BodycamWhite}
    TimeText : text_block = text_block{DefaultTextColor := BodycamWhite}
    LensText : text_block = text_block{DefaultTextColor := BodycamWhite}
    StatusText : text_block = text_block{DefaultTextColor := BodycamWhite}
    CenterText : text_block = text_block{DefaultTextColor := BodycamWhite}
    RadioText : text_block = text_block{DefaultTextColor := BodycamAmber}
    NoSignalText : text_block = text_block{DefaultTextColor := BodycamWhite}

    InjuryTint : color_block = color_block{DefaultColor := BodycamRed, DefaultOpacity := 0.0}
    HitFlash : color_block = color_block{DefaultColor := BodycamRed, DefaultOpacity := 0.0}
    GlitchFlash : color_block = color_block{DefaultColor := BodycamWhite, DefaultOpacity := 0.0}
    NoSignalBackground : color_block = color_block{DefaultColor := BodycamBlack, DefaultOpacity := 1.0}

    Show():void =
        # Ночная смена: камера «включилась» где-то между 00:00 и 04:00.
        set ClockSeconds = GetRandomInt(0, 4 * 3600)

        RecText.SetText(BodycamText("● REC"))
        UnitText.SetText(BodycamText("{CameraModel}  ·  {Callsign}"))
        LensText.SetText(BodycamText("ISO 3200  F2.0  1/30  ·  WIDE"))
        NoSignalText.SetText(BodycamText("НЕТ СИГНАЛА\nSIGNAL LOST · {Callsign}"))
        UpdateTimeText()

        CenterText.SetVisibility(widget_visibility.Collapsed)
        RadioText.SetVisibility(widget_visibility.Collapsed)
        NoSignalBackground.SetVisibility(widget_visibility.Collapsed)
        NoSignalText.SetVisibility(widget_visibility.Collapsed)

        # Порядок слотов задаёт слои: эффекты снизу, «НЕТ СИГНАЛА» поверх всего.
        Root := canvas:
            Slots := array:
                FullScreenSlot(InjuryTint)
                FullScreenSlot(HitFlash)
                FullScreenSlot(GlitchFlash)
                AnchoredSlot(RecText, 0.0, 0.0, 40.0, 30.0)
                AnchoredSlot(UnitText, 0.0, 0.0, 40.0, 60.0)
                AnchoredSlot(TimeText, 1.0, 0.0, -40.0, 30.0)
                AnchoredSlot(StatusText, 0.5, 0.0, 0.0, 30.0)
                AnchoredSlot(CenterText, 0.5, 0.5, 0.0, -120.0)
                AnchoredSlot(RadioText, 0.0, 1.0, 40.0, -30.0)
                AnchoredSlot(LensText, 1.0, 1.0, -40.0, -30.0)
                FullScreenSlot(NoSignalBackground)
                AnchoredSlot(NoSignalText, 0.5, 0.5, 0.0, 0.0)

        if (PlayerUI := GetPlayerUI[Player]):
            PlayerUI.AddWidget(Root, player_ui_slot{InputMode := ui_input_mode.None})
            set MaybeRoot = option{Root}

        spawn{ RunClock() }
        spawn{ RunRecBlink() }

    Hide():void =
        if (PlayerUI := GetPlayerUI[Player], Root := MaybeRoot?):
            PlayerUI.RemoveWidget(Root)
            set MaybeRoot = false

    RunClock()<suspends>:void =
        loop:
            if (not Player.IsActive[]):
                break
            UpdateTimeText()
            Sleep(1.0)
            set ClockSeconds += 1

    UpdateTimeText():void =
        TimeText.SetText(BodycamText("{DateStamp}  {FormatClock(ClockSeconds)}"))

    RunRecBlink()<suspends>:void =
        loop:
            if (not Player.IsActive[]):
                break
            if (IsRecording?):
                RecText.SetVisibility(widget_visibility.Visible)
            Sleep(0.7)
            if (IsRecording?):
                RecText.SetVisibility(widget_visibility.Hidden)
            Sleep(0.5)

    SetStatus(Text:string):void =
        StatusText.SetText(BodycamText(Text))

    # Крупная надпись по центру. Новая надпись отменяет таймер скрытия предыдущей.
    ShowCenter(Text:string, Duration:float)<suspends>:void =
        set CenterToken += 1
        MyToken := CenterToken
        CenterText.SetText(BodycamText(Text))
        CenterText.SetVisibility(widget_visibility.Visible)
        Sleep(Duration)
        if (CenterToken = MyToken):
            CenterText.SetVisibility(widget_visibility.Collapsed)

    # Строчка «рации» в левом нижнем углу.
    ShowRadio(Text:string, Duration:float)<suspends>:void =
        set RadioToken += 1
        MyToken := RadioToken
        RadioText.SetText(BodycamText(Text))
        RadioText.SetVisibility(widget_visibility.Visible)
        Sleep(Duration)
        if (RadioToken = MyToken):
            RadioText.SetVisibility(widget_visibility.Collapsed)

    # Короткая красная вспышка и засветка матрицы при попадании.
    FlashHit()<suspends>:void =
        HitFlash.SetOpacity(0.45)
        GlitchFlash.SetOpacity(0.12)
        Sleep(0.06)
        GlitchFlash.SetOpacity(0.0)
        Sleep(0.06)
        HitFlash.SetOpacity(0.2)
        Sleep(0.1)
        HitFlash.SetOpacity(0.0)

    SetInjured(Injured:logic):void =
        if (Injured?):
            InjuryTint.SetOpacity(0.18)
        else:
            InjuryTint.SetOpacity(0.0)

    SetCameraHudVisible(IsVisible:logic):void =
        Visibility := if (IsVisible?) then widget_visibility.Visible else widget_visibility.Collapsed
        RecText.SetVisibility(Visibility)
        UnitText.SetVisibility(Visibility)
        TimeText.SetVisibility(Visibility)
        LensText.SetVisibility(Visibility)

    # Камера «дёргается», запись останавливается, экран чернеет с надписью «НЕТ СИГНАЛА».
    ShowSignalLost(Seconds:float)<suspends>:void =
        set IsRecording = false
        GlitchFlash.SetOpacity(0.6)
        Sleep(0.05)
        GlitchFlash.SetOpacity(0.0)
        Sleep(0.08)
        GlitchFlash.SetOpacity(0.35)
        Sleep(0.05)
        GlitchFlash.SetOpacity(0.0)
        HitFlash.SetOpacity(0.0)
        InjuryTint.SetOpacity(0.0)
        RecText.SetText(BodycamText("■ STOP"))
        RecText.SetVisibility(widget_visibility.Visible)
        NoSignalBackground.SetVisibility(widget_visibility.Visible)
        NoSignalText.SetVisibility(widget_visibility.Visible)
        Sleep(Seconds)
        NoSignalBackground.SetVisibility(widget_visibility.Collapsed)
        NoSignalText.SetVisibility(widget_visibility.Collapsed)
        # Дальше игрок наблюдает за союзниками, служебные надписи камеры ему уже не нужны.
        SetCameraHudVisible(false)
