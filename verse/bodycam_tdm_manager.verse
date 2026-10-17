# BODYCAM для Fortnite: режим «Командный бой» (Team Deathmatch).
# Две команды, возрождение. Каждое убийство соперника даёт команде очко, убийство своего отнимает.
# Побеждает команда, первой набравшая ScoreToWin, или та, что впереди, когда время вышло.

using { /Fortnite.com/Devices }
using { /Fortnite.com/Playspaces }
using { /Fortnite.com/Teams }
using { /Verse.org/Simulation }

bodycam_tdm_manager := class(bodycam_respawn_mode):

    # Наборы снаряжения на выбор. В каждом Item Granter включите очистку инвентаря при выдаче.
    @editable
    LoadoutGranters : []item_granter_device = array{}

    # Названия наборов для меню, в том же порядке, что LoadoutGranters.
    @editable
    LoadoutNames : []string = array{}

    @editable
    ScoreToWin : int = 50

    var TeamScores : []int = array{0, 0}
    var TeamCounters : []int = array{0, 0}

    ModeTitle<override>():string = "КОМАНДНЫЙ БОЙ"

    PickerOptions<override>():[]string = LoadoutNames

    GrantForPlayer<override>(P:player):void =
        GrantSelected(P, LoadoutGranters)

    GetTeamIndex(InAgent:agent)<transacts>:int =
        TeamCollection := GetPlayspace().GetTeamCollection()
        var Result : int = -1
        for (Index -> Team : TeamCollection.GetTeams(), TeamCollection.IsOnTeam[InAgent, Team]):
            set Result = Index
        Result

    MakeCallsign<override>(P:player):string =
        TeamIndex := GetTeamIndex(P)
        var Number : int = 1
        if (Count := TeamCounters[TeamIndex]):
            set Number = Count + 1
            if (set TeamCounters[TeamIndex] = Number) {}
        "{TeamCallsign(TeamIndex)}-{Number}"

    TeamScore(TeamIndex:int)<transacts>:int =
        if (Value := TeamScores[TeamIndex]) then Value else 0

    AddTeamScore(TeamIndex:int, Delta:int):void =
        if (Old := TeamScores[TeamIndex], set TeamScores[TeamIndex] = Max(Old + Delta, 0)) {}

    OnKill<override>(Killer:player, Victim:player):void =
        KillerTeam := GetTeamIndex(Killer)
        if (KillerTeam = GetTeamIndex(Victim)):
            AddTeamScore(KillerTeam, -1)
        else:
            AddTeamScore(KillerTeam, 1)
            if (TeamScore(KillerTeam) >= ScoreToWin):
                FinishMatch(Killer)

    OnSuicide<override>(Victim:player):void = {}

    StatusFor<override>(P:player):string =
        "ALPHA {TeamScore(0)} : {TeamScore(1)} BRAVO  ·  ДО {ScoreToWin}"

    WinnerText<override>(Winner:player):string =
        "ПОБЕДА {TeamCallsign(GetTeamIndex(Winner))}\nALPHA {TeamScore(0)} : {TeamScore(1)} BRAVO"

    TimeUpWinner<override>():?player =
        if (TeamScore(0) > TeamScore(1)):
            FindPlayerOnTeam(0)
        else if (TeamScore(1) > TeamScore(0)):
            FindPlayerOnTeam(1)
        else:
            false

    FindPlayerOnTeam(TeamIndex:int):?player =
        var Result : ?player = false
        for (P -> BodycamAgent : Agents, P.IsActive[], GetTeamIndex(P) = TeamIndex):
            set Result = option{P}
        Result
