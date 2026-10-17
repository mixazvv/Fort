# BODYCAM для Fortnite: режим Deathmatch.
# Каждый сам за себя, возрождение. Побеждает тот, кто первым наберёт KillsToWin убийств
# или у кого больше убийств, когда время вышло. Смерть без убийцы отнимает одно очко.
# Снаряжение выбирается в меню на экране «НЕТ СИГНАЛА» и выдаётся при возрождении.

using { /Fortnite.com/Devices }

bodycam_deathmatch_manager := class(bodycam_respawn_mode):

    # Наборы снаряжения на выбор. В каждом Item Granter включите очистку инвентаря при выдаче.
    @editable
    LoadoutGranters : []item_granter_device = array{}

    # Названия наборов для меню, в том же порядке, что LoadoutGranters.
    @editable
    LoadoutNames : []string = array{}

    @editable
    KillsToWin : int = 25

    var Kills : [player]int = map{}

    ModeTitle<override>():string = "DEATHMATCH"

    GetKills(P:player):int =
        if (Value := Kills[P]) then Value else 0

    PickerOptions<override>():[]string = LoadoutNames

    GrantForPlayer<override>(P:player):void =
        GrantSelected(P, LoadoutGranters)

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
