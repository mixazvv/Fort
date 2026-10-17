# BODYCAM для Fortnite: режим «Гонка вооружений» (Gun Game).
# Каждый сам за себя, возрождение. Каждое убийство сразу меняет оружие на следующее по списку.
# Побеждает тот, кто сделает убийство последним оружием или продвинулся дальше всех, когда время вышло.
# Смерть без убийцы (падение, самоподрыв) откатывает на одно оружие назад.

using { /Fortnite.com/Devices }
using { /Verse.org/Simulation }

bodycam_gungame_manager := class(bodycam_respawn_mode):

    # Оружие по порядку, от сильного к слабому. Каждый Item Granter выдаёт одно оружие
    # с запасом патронов и очищает инвентарь при выдаче.
    @editable
    WeaponTiers : []item_granter_device = array{}

    # Названия оружия для экрана, в том же порядке, что WeaponTiers.
    @editable
    TierNames : []string = array{}

    @editable
    DemoteOnSuicide : logic = true

    var Levels : [player]int = map{}

    ModeTitle<override>():string = "ГОНКА ВООРУЖЕНИЙ"

    # Оружие выдаёт сама гонка, арсенал на экране смерти не нужен.
    UsesArsenal<override>()<transacts>:logic = false

    GetLevel(P:player)<transacts>:int =
        if (Value := Levels[P]) then Value else 0

    TierName(Level:int):string =
        if (Name := TierNames[Level]) then Name else "ОРУЖИЕ {Level + 1}"

    GrantForPlayer<override>(P:player):void =
        if (Granter := WeaponTiers[GetLevel(P)]):
            Granter.GrantItem(P)

    OnKill<override>(Killer:player, Victim:player):void =
        NewLevel := GetLevel(Killer) + 1
        if (NewLevel >= WeaponTiers.Length):
            FinishMatch(Killer)
        else:
            if (set Levels[Killer] = NewLevel) {}
            # Оружие меняется сразу, прямо в бою.
            GrantForPlayer(Killer)
            if (KillerBodycam := Agents[Killer]):
                spawn{ KillerBodycam.Overlay.ShowCenter("{TierName(NewLevel)}", 1.5) }

    OnSuicide<override>(Victim:player):void =
        if (DemoteOnSuicide?):
            if (set Levels[Victim] = Max(GetLevel(Victim) - 1, 0)) {}

    StatusFor<override>(P:player):string =
        Mine := "{GetLevel(P) + 1}/{WeaponTiers.Length}  {TierName(GetLevel(P))}"
        if (Leader := FindLeader(Levels)?, Leader <> P):
            "{Mine}  ·  ЛИДЕР {CallsignOf(Leader)} ({GetLevel(Leader) + 1})"
        else:
            Mine

    TimeUpWinner<override>():?player =
        FindLeader(Levels)
