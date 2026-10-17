# BODYCAM для Fortnite: общая основа режимов с возрождением (Deathmatch, Гонка вооружений).
# Каждый сам за себя, матч по времени или до победного счёта.
# На уровень эту основу не ставят: ставят bodycam_deathmatch_manager или bodycam_gungame_manager.

using { /Fortnite.com/Devices }
using { /Fortnite.com/Characters }
using { /Fortnite.com/Playspaces }
using { /Verse.org/Simulation }

bodycam_respawn_mode := class<abstract>(creative_device, bodycam_mode):

    # --- Обязательные устройства ---

    # End Game (режим «Игра», победитель: активировавший игрок).
    @editable
    EndGame : end_game_device = end_game_device{}

    # Все Player Spawner карты. По их событиям оружие и здоровье выдаются при каждом возрождении.
    @editable
    Spawners : []player_spawner_device = array{}

    # --- Необязательные устройства ---

    @editable
    MovementModulators : []movement_modulator_device = array{}

    @editable
    InjuredSounds : []audio_player_device = array{}

    @editable
    BreathingSounds : []audio_player_device = array{}

    # Короткий щелчок или подтверждение по рации после убийства (только убийце).
    @editable
    KillConfirmSounds : []audio_player_device = array{}

    # --- Правила ---

    @editable
    MatchSeconds : int = 600

    @editable
    MaxHealth : float = 45.0

    @editable
    InjuredHealthFraction : float = 0.5

    @editable
    HeavyBreathingAfterSeconds : float = 4.0

    # Должно быть меньше времени возрождения из Island Settings.
    @editable
    SignalLostSeconds : float = 2.5

    @editable
    ResultScreenSeconds : float = 6.0

    # --- Оформление оверлея ---

    @editable
    CameraModel : string = "BWC-4"

    @editable
    DateStamp : string = "2026-10-17"

    var Agents : [player]bodycam_agent = map{}
    var NextUnitNumber : int = 1
    var MatchOver : logic = false

    # --- Что определяет конкретный режим ---

    # Выдать оружие при возрождении.
    GrantForPlayer(P:player):void
    # Засчитать убийство. Режим сам вызывает FinishMatch, если кто-то победил.
    OnKill(Killer:player, Victim:player):void
    # Смерть без убийцы: падение, самоподрыв.
    OnSuicide(Victim:player):void
    # Строка статуса вверху экрана (без таймера).
    StatusFor(P:player):string
    # Кто победил, если время вышло.
    TimeUpWinner():?player
    # Название режима для заставки.
    ModeTitle():string

    OnBegin<override>()<suspends>:void =
        for (Spawner : Spawners):
            Spawner.SpawnedEvent().Subscribe(OnSpawned)
        GetPlayspace().PlayerAddedEvent().Subscribe(OnPlayerAdded)

        Sleep(0.5)
        for (P : GetPlayspace().GetPlayers()):
            HandleSpawn(P)

        BroadcastCenter("{ModeTitle()}\nСМЕНА НАЧАЛАСЬ", 4.0)
        RunMatchTimer()

    # ---------- Игроки ----------

    OnPlayerAdded(P:player):void =
        EnsurePlayer(P)

    OnSpawned(SpawnedAgent:agent):void =
        if (P := player[SpawnedAgent]):
            HandleSpawn(P)

    EnsurePlayer(P:player):void =
        if (not Agents[P]):
            Callsign := "UNIT-{Pad2(NextUnitNumber)}"
            set NextUnitNumber += 1
            Overlay := bodycam_overlay{Player := P, Callsign := Callsign, CameraModel := CameraModel, DateStamp := DateStamp}
            Feel := bodycam_feel:
                InjuredHealthFraction := InjuredHealthFraction
                HeavyBreathingAfterSeconds := HeavyBreathingAfterSeconds
                SignalLostSeconds := SignalLostSeconds
            BodycamAgent := bodycam_agent{Player := P, Mode := Self, Feel := Feel, Overlay := Overlay}
            if (set Agents[P] = BodycamAgent) {}
            Overlay.Show()

    HandleSpawn(P:player):void =
        EnsurePlayer(P)
        if (BodycamAgent := Agents[P], Character := P.GetFortCharacter[]):
            BodycamAgent.Bind(Character)
            BodycamAgent.OnRespawned()
            Character.SetMaxHealth(MaxHealth)
            Character.SetHealth(MaxHealth)
            Character.SetShield(0.0)
            for (Modulator : MovementModulators):
                Modulator.Activate(P)
            if (not MatchOver?):
                GrantForPlayer(P)
            BodycamAgent.Overlay.SetStatus(StatusFor(P))

    CallsignOf(P:player):string =
        if (BodycamAgent := Agents[P]) then BodycamAgent.Callsign() else "UNIT"

    # ---------- События игрока ----------

    OnAgentEliminated<override>(Victim:bodycam_agent, Killer:?agent):void =
        if (not MatchOver?):
            if (KillerAgent := Killer?, KillerPlayer := player[KillerAgent], KillerPlayer <> Victim.Player):
                PlaySoundsFor(KillConfirmSounds, KillerPlayer)
                if (KillerBodycam := Agents[KillerPlayer]):
                    spawn{ KillerBodycam.Overlay.ShowRadio("РАЦИЯ › {Victim.Callsign()}: цель нейтрализована", 3.0) }
                OnKill(KillerPlayer, Victim.Player)
            else:
                OnSuicide(Victim.Player)
            RefreshStatus()

    OnAgentInjured<override>(Victim:bodycam_agent):void =
        PlaySoundsFor(InjuredSounds, Victim.Player)

    OnAgentWinded<override>(Victim:bodycam_agent):void =
        PlaySoundsFor(BreathingSounds, Victim.Player)

    # ---------- Матч ----------

    RunMatchTimer()<suspends>:void =
        var Remaining : int = MatchSeconds
        loop:
            if (MatchOver? or Remaining <= 0):
                break
            for (P -> BodycamAgent : Agents):
                BodycamAgent.Overlay.SetStatus("{StatusFor(P)}  ·  {FormatTimer(Remaining)}")
            Sleep(1.0)
            set Remaining -= 1
        if (not MatchOver?):
            # Если за матч никто ничего не набрал, побеждает любой оставшийся игрок.
            var Winner : ?player = TimeUpWinner()
            if (not Winner?):
                for (P -> BodycamAgent : Agents, P.IsActive[]):
                    set Winner = option{P}
            if (W := Winner?):
                FinishMatch(W)

    RefreshStatus():void =
        for (P -> BodycamAgent : Agents):
            BodycamAgent.Overlay.SetStatus(StatusFor(P))

    FinishMatch(Winner:player):void =
        if (not MatchOver?):
            set MatchOver = true
            spawn{ RunMatchEnd(Winner) }

    RunMatchEnd(Winner:player)<suspends>:void =
        BroadcastCenter("КОНЕЦ СМЕНЫ\nЛУЧШИЙ: {CallsignOf(Winner)}", ResultScreenSeconds)
        Sleep(ResultScreenSeconds)
        EndGame.Activate(Winner)

    BroadcastCenter(Text:string, Duration:float):void =
        for (P -> BodycamAgent : Agents):
            spawn{ BodycamAgent.Overlay.ShowCenter(Text, Duration) }

    # Игрок с наибольшим значением Score. Используется режимами для лидера и победителя по времени.
    FindLeader(Score:[player]int):?player =
        var Leader : ?player = false
        var Best : int = -1
        for (P -> Value : Score, P.IsActive[], Value > Best):
            set Best = Value
            set Leader = option{P}
        Leader
