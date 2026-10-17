# BODYCAM для Fortnite: режим Deathmatch.
# Каждый сам за себя, возрождение. Побеждает тот, кто первым наберёт KillsToWin убийств
# или у кого больше убийств, когда время вышло. Смерть без убийцы отнимает одно очко.
# Снаряжение собирается в арсенале (лобби и экран «НЕТ СИГНАЛА») и выдаётся при возрождении.

using { /Fortnite.com/Devices }
using { /Verse.org/Simulation }

bodycam_deathmatch_manager := class(bodycam_respawn_mode):

    @editable
    KillsToWin : int = 25

    var Kills : [player]int = map{}

    ModeTitle<override>():string = "DEATHMATCH"

    GetKills(P:player)<transacts>:int =
        if (Value := Kills[P]) then Value else 0

    OnKill<override>(Killer:player, Victim:player):void =
        NewKills := GetKills(Killer) + 1
        if (set Kills[Killer] = NewKills) {}
        if (NewKills >= KillsToWin):
            FinishMatch(Killer)

    OnSuicide<override>(Victim:player):void =
        if (set Kills[Victim] = Max(GetKills(Victim) - 1, 0)) {}

    StatusFor<override>(P:player):string =
        Mine := "УБИЙСТВ {GetKills(P)}/{KillsToWin}"
        if (Leader := FindLeader(Kills)?, Leader <> P):
            "{Mine}  ·  ЛИДЕР {CallsignOf(Leader)} ({GetKills(Leader)})"
        else:
            Mine

    TimeUpWinner<override>():?player =
        FindLeader(Kills)
