# BODYCAM для Fortnite: реакция одного игрока на события персонажа
# (урон, выбывание, бег, возрождение). Что из этого следует для матча, решает режим (bodycam_mode).

using { /Fortnite.com/Characters }
using { /Fortnite.com/Game }
using { /Verse.org/Simulation }

bodycam_agent := class:
    Player : player
    Mode : bodycam_mode
    Feel : bodycam_feel
    Overlay : bodycam_overlay

    var SprintStartTime : float = 0.0
    var IsInjured : logic = false
    var IsDown : logic = false
    var IsBound : logic = false

    Callsign():string = Overlay.Callsign

    # Подписка выполняется один раз: персонаж игрока переживает возрождения.
    Bind(Character:fort_character):void =
        if (not IsBound?):
            set IsBound = true
            Character.DamagedEvent().Subscribe(OnDamaged)
            Character.EliminatedEvent().Subscribe(OnEliminated)
            Character.SprintedEvent().Subscribe(OnSprinted)

    # Для режимов с возрождением.
    OnRespawned():void =
        set IsDown = false
        set IsInjured = false
        set SprintStartTime = GetSimulationElapsedTime()
        Overlay.ResetForRespawn()

    OnDamaged(Result:damage_result):void =
        if (not IsDown?):
            spawn{ Overlay.FlashHit() }
            if:
                not IsInjured?
                Character := Player.GetFortCharacter[]
                Character.GetHealth() <= Character.GetMaxHealth() * Feel.InjuredHealthFraction
            then:
                set IsInjured = true
                Overlay.SetInjured(true)
                Mode.OnAgentInjured(Self)

    OnEliminated(Result:elimination_result):void =
        if (not IsDown?):
            set IsDown = true
            spawn{ Overlay.ShowSignalLost(Feel.SignalLostSeconds) }
            var Killer : ?agent = false
            if (KillerCharacter := Result.EliminatingCharacter?, KillerAgent := KillerCharacter.GetAgent[]):
                set Killer = option{KillerAgent}
            Mode.OnAgentEliminated(Self, Killer)

    # После долгого бега игрок тяжело дышит в микрофон камеры.
    OnSprinted(Payload:tuple(fort_character, logic)):void =
        Now := GetSimulationElapsedTime()
        if (Payload(1)?):
            set SprintStartTime = Now
        else if (not IsDown?, Now - SprintStartTime >= Feel.HeavyBreathingAfterSeconds):
            Mode.OnAgentWinded(Self)
