# BODYCAM для Fortnite: режим «Раунды» (командный, без возрождений).
# 5 на 5, раунды, одна жизнь за раунд. Раунд выигрывает команда, которая
# уничтожила соперников, а по истечении времени та, у которой больше живых (потом больше здоровья).
# Матч выигрывает команда, первой взявшая RoundsToWin раундов.
#
# Раунды собраны на стандартной системе раундов Fortnite: в начале каждого
# раунда Verse-устройства перезапускаются, поэтому счёт матча хранится в
# weak_map(session, ...), который живёт всю игровую сессию.

using { /Fortnite.com/Devices }
using { /Fortnite.com/Characters }
using { /Fortnite.com/Playspaces }
using { /Fortnite.com/Teams }
using { /Verse.org/Simulation }
using { /Verse.org/Random }

bodycam_match_state := struct:
    RoundNumber : int = 1
    Scores : []int = array{0, 0}

var BodycamMatchStates : weak_map(session, bodycam_match_state) = map{}

bodycam_rounds_manager := class(creative_device, bodycam_mode):

    # --- Обязательные устройства ---

    # Round Settings: завершает раунд и передаёт победу команде указанного игрока.
    @editable
    RoundSettings : round_settings_device = round_settings_device{}

    # End Game (режим «Игра»): завершает матч, когда кто-то набрал RoundsToWin.
    @editable
    EndGame : end_game_device = end_game_device{}

    # --- Необязательные устройства (можно оставить пустыми) ---

    # Наборы оружия. Каждый раунд выбирается один случайный, одинаковый для всех.
    @editable
    LoadoutGranters : []item_granter_device = array{}

    # Замедление шага для «тяжёлого» передвижения (скорость около 0.85).
    @editable
    MovementModulators : []movement_modulator_device = array{}

    # Сердцебиение и тяжёлое дыхание при ранении.
    @editable
    InjuredSounds : []audio_player_device = array{}

    # Одышка после долгого бега.
    @editable
    BreathingSounds : []audio_player_device = array{}

    # Хрип рации, когда напарник выбывает.
    @editable
    RadioSounds : []audio_player_device = array{}

    # Звуки старта раунда для всех: сирена, радиопереговоры диспетчера.
    @editable
    RoundStartSounds : []audio_player_device = array{}

    # --- Правила ---

    @editable
    RoundsToWin : int = 5

    @editable
    PrepSeconds : int = 10

    @editable
    RoundSeconds : int = 180

    # Максимальное здоровье. При 45 HP из штурмовой винтовки Fortnite убивают за 2 попадания в тело и за 1 в голову.
    @editable
    MaxHealth : float = 45.0

    # Ниже этой доли здоровья включаются красная виньетка и сердцебиение.
    @editable
    InjuredHealthFraction : float = 0.5

    @editable
    HeavyBreathingAfterSeconds : float = 4.0

    @editable
    SignalLostSeconds : float = 3.5

    @editable
    ResultScreenSeconds : float = 5.0

    # --- Оформление оверлея ---

    @editable
    CameraModel : string = "BWC-4"

    @editable
    DateStamp : string = "2026-10-17"

    var Agents : [player]bodycam_agent = map{}
    var Alive : [player]logic = map{}
    var Scores : []int = array{0, 0}
    var RoundNumber : int = 1
    var InPrep : logic = true
    var RoundOver : logic = false
    var RoundWinner : int = -1
    RoundEndedEvent : event() = event(){}

    OnBegin<override>()<suspends>:void =
        LoadMatchState()
        # Даём персонажам заспавниться.
        Sleep(0.5)

        var TeamCounters : []int = array{0, 0}
        for (P : GetPlayspace().GetPlayers()):
            TeamIndex := GetTeamIndex(P)
            var Number : int = 1
            if (Count := TeamCounters[TeamIndex]):
                set Number = Count + 1
                if (set TeamCounters[TeamIndex] = Number) {}
            SetupPlayer(P, "{TeamCallsign(TeamIndex)}-{Number}")

        GetPlayspace().PlayerAddedEvent().Subscribe(OnPlayerAdded)
        GetPlayspace().PlayerRemovedEvent().Subscribe(OnPlayerRemoved)

        RunRound()

    # ---------- Игроки ----------

    SetupPlayer(P:player, Callsign:string):void =
        Overlay := bodycam_overlay{Player := P, Callsign := Callsign, CameraModel := CameraModel, DateStamp := DateStamp}
        Feel := bodycam_feel:
            InjuredHealthFraction := InjuredHealthFraction
            HeavyBreathingAfterSeconds := HeavyBreathingAfterSeconds
            SignalLostSeconds := SignalLostSeconds
        BodycamAgent := bodycam_agent{Player := P, Mode := Self, Feel := Feel, Overlay := Overlay}
        if (set Agents[P] = BodycamAgent) {}
        Overlay.Show()

        if (Character := P.GetFortCharacter[]):
            BodycamAgent.Bind(Character)
            ApplyLethality(Character)
            # Игрок, зашедший посреди раунда, ждёт следующего.
            if (InPrep?):
                if (set Alive[P] = true) {}
                Character.PutInStasis(stasis_args{AllowTurning := true, AllowFalling := true, AllowEmotes := false})

        for (Modulator : MovementModulators):
            Modulator.Activate(P)

    OnPlayerAdded(P:player):void =
        TeamIndex := GetTeamIndex(P)
        SetupPlayer(P, "{TeamCallsign(TeamIndex)}-{GetRandomInt(6, 9)}")

    OnPlayerRemoved(P:player):void =
        if (set Alive[P] = false) {}
        CheckRoundEnd()

    ApplyLethality(Character:fort_character):void =
        Character.SetMaxHealth(MaxHealth)
        Character.SetHealth(MaxHealth)
        Character.SetShield(0.0)

    GetTeamIndex(InAgent:agent):int =
        TeamCollection := GetPlayspace().GetTeamCollection()
        var Result : int = -1
        for (Index -> Team : TeamCollection.GetTeams(), TeamCollection.IsOnTeam[InAgent, Team]):
            set Result = Index
        Result

    CountAlive(TeamIndex:int):int =
        var Count : int = 0
        for (P -> IsAlive : Alive, IsAlive?, P.IsActive[], GetTeamIndex(P) = TeamIndex):
            set Count += 1
        Count

    TeamHealth(TeamIndex:int):float =
        var Total : float = 0.0
        for (P -> IsAlive : Alive, IsAlive?, GetTeamIndex(P) = TeamIndex, Character := P.GetFortCharacter[]):
            set Total += Character.GetHealth()
        Total

    FindPlayerOnTeam(TeamIndex:int):?player =
        var Result : ?player = false
        for (P -> BodycamAgent : Agents, P.IsActive[], GetTeamIndex(P) = TeamIndex):
            set Result = option{P}
        Result

    AnyPlayer():?player =
        var Result : ?player = false
        for (P -> BodycamAgent : Agents, P.IsActive[]):
            set Result = option{P}
        Result

    # ---------- Ход раунда ----------

    RunRound()<suspends>:void =
        # 1. Подготовка: все стоят на месте и могут только осматриваться.
        set InPrep = true
        GrantRoundLoadout()
        BroadcastCenter("РАУНД {RoundNumber}\n{ScoreLine()}", 4.0)
        var Remaining : int = PrepSeconds
        loop:
            if (Remaining <= 0):
                break
            SetStatusForAll("ПОДГОТОВКА  ·  {FormatTimer(Remaining)}")
            Sleep(1.0)
            set Remaining -= 1

        # 2. Бой.
        set InPrep = false
        for (P -> BodycamAgent : Agents, Character := P.GetFortCharacter[]):
            Character.ReleaseFromStasis()
        for (Sound : RoundStartSounds):
            Sound.Play()
        BroadcastCenter("ВПЕРЁД", 1.5)
        # Кто-то мог выйти во время подготовки.
        CheckRoundEnd()

        race:
            RoundEndedEvent.Await()
            RunRoundTimer()
        if (not RoundOver?):
            ResolveTimeout()

        # 3. Итоги.
        SaveMatchState()
        ResultText := if (RoundWinner >= 0) then "РАУНД ЗА {TeamCallsign(RoundWinner)}" else "НИЧЬЯ"
        IsMatchOver := if (WinnerScore := Scores[RoundWinner], WinnerScore >= RoundsToWin) then true else false
        if (IsMatchOver?):
            BroadcastCenter("{ResultText}\n{ScoreLine()}\n\nМАТЧ ЗА {TeamCallsign(RoundWinner)}", ResultScreenSeconds)
        else:
            BroadcastCenter("{ResultText}\n{ScoreLine()}", ResultScreenSeconds)
        SetStatusForAll(ScoreLine())
        Sleep(ResultScreenSeconds)

        var EndingPlayer : ?player = FindPlayerOnTeam(RoundWinner)
        if (not EndingPlayer?):
            set EndingPlayer = AnyPlayer()
        if (P := EndingPlayer?):
            if (IsMatchOver?):
                EndGame.Activate(P)
            else:
                RoundSettings.EndRound(P)

    RunRoundTimer()<suspends>:void =
        var Remaining : int = RoundSeconds
        loop:
            if (Remaining <= 0):
                break
            SetStatusForAll("{ScoreLine()}  ·  {FormatTimer(Remaining)}")
            Sleep(1.0)
            set Remaining -= 1

    OnAgentEliminated<override>(Victim:bodycam_agent, Killer:?agent):void =
        P := Victim.Player
        Callsign := Victim.Callsign()
        if (set Alive[P] = false) {}
        TeamIndex := GetTeamIndex(P)
        for (Mate -> BodycamAgent : Agents, Mate <> P, GetTeamIndex(Mate) = TeamIndex):
            spawn{ BodycamAgent.Overlay.ShowRadio("РАЦИЯ › {Callsign}: нет связи", 4.0) }
            for (Sound : RadioSounds):
                Sound.Play(Mate)
        CheckRoundEnd()

    CheckRoundEnd():void =
        if (not RoundOver?, not InPrep?):
            AliveA := CountAlive(0)
            AliveB := CountAlive(1)
            if (AliveA = 0, AliveB = 0):
                FinishRound(-1)
            else if (AliveA = 0):
                FinishRound(1)
            else if (AliveB = 0):
                FinishRound(0)

    # Время вышло: побеждает команда с большим числом живых, потом с большим суммарным здоровьем.
    ResolveTimeout():void =
        AliveA := CountAlive(0)
        AliveB := CountAlive(1)
        if (AliveA > AliveB):
            FinishRound(0)
        else if (AliveB > AliveA):
            FinishRound(1)
        else:
            HealthA := TeamHealth(0)
            HealthB := TeamHealth(1)
            if (HealthA > HealthB):
                FinishRound(0)
            else if (HealthB > HealthA):
                FinishRound(1)
            else:
                FinishRound(-1)

    FinishRound(WinnerTeam:int):void =
        if (not RoundOver?):
            set RoundOver = true
            set RoundWinner = WinnerTeam
            if (Old := Scores[WinnerTeam], set Scores[WinnerTeam] = Old + 1) {}
            RoundEndedEvent.Signal()

    GrantRoundLoadout():void =
        if (Granter := LoadoutGranters[GetRandomInt(0, LoadoutGranters.Length - 1)]):
            for (P -> BodycamAgent : Agents):
                Granter.GrantItem(P)

    # ---------- Звук ----------

    OnAgentInjured<override>(Victim:bodycam_agent):void =
        PlaySoundsFor(InjuredSounds, Victim.Player)

    OnAgentWinded<override>(Victim:bodycam_agent):void =
        PlaySoundsFor(BreathingSounds, Victim.Player)

    # ---------- Оверлей ----------

    ScoreLine():string =
        if (A := Scores[0], B := Scores[1]):
            "ALPHA {A} : {B} BRAVO"
        else:
            ""

    BroadcastCenter(Text:string, Duration:float):void =
        for (P -> BodycamAgent : Agents):
            spawn{ BodycamAgent.Overlay.ShowCenter(Text, Duration) }

    SetStatusForAll(Text:string):void =
        for (P -> BodycamAgent : Agents):
            BodycamAgent.Overlay.SetStatus(Text)

    # ---------- Счёт матча между раундами ----------

    LoadMatchState():void =
        if (State := BodycamMatchStates[GetSession()]):
            set RoundNumber = State.RoundNumber
            set Scores = State.Scores

    SaveMatchState():void =
        NewState := bodycam_match_state{RoundNumber := RoundNumber + 1, Scores := Scores}
        if (set BodycamMatchStates[GetSession()] = NewState) {}
