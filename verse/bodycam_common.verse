# BODYCAM для Fortnite: общие типы, утилиты, цвета и форматирование текста.

using { /Fortnite.com/Devices }
using { /Verse.org/Colors }

# Превращает строку в message для виджетов UI.
BodycamText<localizes>(S:string):message = "{S}"

# Палитра оверлея нагрудной камеры: выцветший белый, красный REC, янтарная рация.
BodycamWhite : color = color{R := 0.93, G := 0.93, B := 0.88}
BodycamRed : color = color{R := 0.85, G := 0.05, B := 0.05}
BodycamAmber : color = color{R := 1.0, G := 0.75, B := 0.2}
BodycamBlack : color = color{R := 0.0, G := 0.0, B := 0.0}

# Реакции игрока, одинаковые для всех режимов.
bodycam_feel := struct:
    InjuredHealthFraction : float = 0.5
    HeavyBreathingAfterSeconds : float = 4.0
    SignalLostSeconds : float = 3.5

# То, что каждый режим (раунды, deathmatch, гонка вооружений) делает по событиям игрока.
bodycam_mode := interface:
    OnAgentEliminated(Victim:bodycam_agent, Killer:?agent):void
    OnAgentHit(Victim:bodycam_agent):void
    OnAgentInjured(Victim:bodycam_agent):void
    OnAgentWinded(Victim:bodycam_agent):void

PlaySoundsFor(Sounds:[]audio_player_device, Target:agent):void =
    for (Sound : Sounds):
        Sound.Play(Target)

Pad2(N:int):string =
    if (N < 10) then "0{N}" else "{N}"

# 8125 -> "02:15:25"
FormatClock(TotalSeconds:int):string =
    if:
        Day := Mod[TotalSeconds, 86400]
        H := Quotient[Day, 3600]
        Rest := Mod[Day, 3600]
        M := Quotient[Rest, 60]
        S := Mod[Rest, 60]
    then:
        "{Pad2(H)}:{Pad2(M)}:{Pad2(S)}"
    else:
        "00:00:00"

# 95 -> "1:35"
FormatTimer(TotalSeconds:int):string =
    Clamped := Max(TotalSeconds, 0)
    if (M := Quotient[Clamped, 60], S := Mod[Clamped, 60]):
        "{M}:{Pad2(S)}"
    else:
        "0:00"

# Позывной команды по её индексу в коллекции команд.
TeamCallsign(TeamIndex:int):string =
    case (TeamIndex):
        0 => "ALPHA"
        1 => "BRAVO"
        _ => "UNIT"
