# BODYCAM для Fortnite: общая основа режимов с возрождением (Deathmatch, Гонка вооружений).
# Матч по времени или до победного счёта.
# На уровень эту основу не ставят: ставят bodycam_deathmatch_manager, bodycam_tdm_manager или bodycam_gungame_manager.

using { /Fortnite.com/Devices }
using { /Fortnite.com/Characters }
using { /Fortnite.com/Playspaces }
using { /Verse.org/Simulation }
using { /Verse.org/Random }

bodycam_respawn_mode := class(creative_device, bodycam_mode):

    # --- Обязательные устройства ---

    # End Game (режим «Игра», победитель: активировавший игрок).
    @editable
    EndGame : end_game_device = end_game_device{}

    # Все Player Spawner на карте (не в лобби). По их событиям оружие и здоровье выдаются при каждом
    # возрождении. Пока идёт лобби, они выключены.
    @editable
    Spawners : []player_spawner_device = array{}

    # Арсенал: из него выдаётся собранное игроком снаряжение.
    @editable
    Arsenal : bodycam_arsenal_device = bodycam_arsenal_device{}

    # Лобби «Брифинг». Если не настроено, матч стартует сразу.
    @editable
    Lobby : bodycam_lobby_device = bodycam_lobby_device{}

    # --- Необязательные устройства ---

    @editable
    MovementModulators : []movement_modulator_device = array{}

    # Короткое замедление после попадания (Movement Modulator: 0.6 на 1 с).
    @editable
    HitSlowModulators : []movement_modulator_device = array{}

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

    # Должно быть меньше времени возрождения из Island Settings (5 с).
    # Пока экран чёрный, можно выбрать снаряжение на следующую жизнь.
    @editable
    SignalLostSeconds : float = 4.0

    # Показывать убийце «цель нейтрализована». Выключите для хардкора: о попадании узнаёшь только по тишине.
    @editable
    ConfirmKills : logic = true

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
    var MatchStarted : logic = false

    # --- Что определяет конкретный режим ---

    # Устройства Fortnite не могут быть абстрактными, поэтому здесь пустые реализации по умолчанию.

    # Выдать оружие при возрождении. По умолчанию — снаряжение из арсенала.
    GrantForPlayer(P:player):void =
        Arsenal.Grant(P)
    # Засчитать убийство. Режим сам вызывает FinishMatch, если кто-то победил.
    OnKill(Killer:player, Victim:player):void = {}
    # Смерть без убийцы: падение, самоподрыв.
    OnSuicide(Victim:player):void = {}
    # Строка статуса вверху экрана (без таймера).
    StatusFor(P:player):string = ""
    # Кто победил, если время вышло.
    TimeUpWinner():?player = false
    # Название режима для заставки.
    ModeTitle():string = "BODYCAM"

    # --- Что режим может переопределить ---

    # Позывной нового игрока.
    MakeCallsign(P:player):string =
        Callsign := "UNIT-{Pad2(NextUnitNumber)}"
        set NextUnitNumber += 1
        Callsign

    # Открывать ли арсенал на экране смерти (в «Гонке вооружений» оружие выдаёт сама гонка).
    UsesArsenal()<transacts>:logic = true

    # Текст на экране конца матча.
    WinnerText(Winner:player):string = "ЛУЧШИЙ: {CallsignOf(Winner)}"

    OnBegin<override>()<suspends>:void =
        GetPlayspace().PlayerAddedEvent().Subscribe(OnPlayerAdded)

        # Лобби: спавны карты выключены, игроки собирают снаряжение в брифинге.
        if (Lobby.IsConfigured()?):
            for (Spawner : Spawners):
                Spawner.Disable()
            Lobby.RunLobby(Arsenal, ModeTitle())

        # Матч: включаем спавны карты и переносим туда всех из лобби.
        for (Spawner : Spawners):
            Spawner.Enable()
            Spawner.SpawnedEvent.Subscribe(OnSpawned)
        set MatchStarted = true
        Sleep(0.2)
        for (P : GetPlayspace().GetPlayers()):
            if (Lobby.IsConfigured()?, Spawner := Spawners[GetRandomInt(0, Spawners.Length - 1)]):
                TeleportToDevice(P, Spawner)
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
            Callsign := MakeCallsign(P)
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
        if (MatchStarted?, BodycamAgent := Agents[P], Character := P.GetFortCharacter[]):
            BodycamAgent.Bind(Character)
            Arsenal.CloseMenu(P)
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
                if (ConfirmKills?, KillerBodycam := Agents[KillerPlayer]):
                    PlaySoundsFor(KillConfirmSounds, KillerPlayer)
                    spawn{ KillerBodycam.Overlay.ShowRadio("РАЦИЯ › {Victim.Callsign()}: цель нейтрализована", 3.0) }
                OnKill(KillerPlayer, Victim.Player)
            else:
                OnSuicide(Victim.Player)
            RefreshStatus()
            if (not MatchOver?, UsesArsenal()?):
                Arsenal.OpenMenu(Victim.Player, "СНАРЯЖЕНИЕ · СЛЕДУЮЩАЯ ЖИЗНЬ", false)

    OnAgentHit<override>(Victim:bodycam_agent):void =
        for (Modulator : HitSlowModulators):
            Modulator.Activate(Victim.Player)

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
        Arsenal.CloseAll()
        BroadcastCenter("КОНЕЦ СМЕНЫ\n{WinnerText(Winner)}", ResultScreenSeconds)
        Sleep(ResultScreenSeconds)
        EndGame.Activate(Winner)

    BroadcastCenter(Text:string, Duration:float):void =
        for (P -> BodycamAgent : Agents):
            spawn{ BodycamAgent.Overlay.ShowCenter(Text, Duration) }

    # Игрок с наибольшим значением Score. Используется режимами для лидера и победителя по времени.
    FindLeader(Score:[player]int)<transacts>:?player =
        var Leader : ?player = false
        var Best : int = -1
        for (P -> Value : Score, P.IsActive[], Value > Best):
            set Best = Value
            set Leader = option{P}
        Leader
