# BODYCAM для Fortnite: реакция одного игрока на события персонажа
# (урон, выбывание, бег) и связь с менеджером раунда.

using { /Fortnite.com/Characters }
using { /Fortnite.com/Game }
using { /Verse.org/Simulation }

bodycam_agent := class:
    Player : player
    Manager : bodycam_game_manager
    Overlay : bodycam_overlay

    var SprintStartTime : float = 0.0
    var IsInjured : logic = false
    var IsDown : logic = false

    Bind(Character:fort_character):void =
        Character.DamagedEvent().Subscribe(OnDamaged)
        Character.EliminatedEvent().Subscribe(OnEliminated)
        Character.SprintedEvent().Subscribe(OnSprinted)

    OnDamaged(Result:damage_result):void =
        if (not IsDown?):
            spawn{ Overlay.FlashHit() }
            if:
                not IsInjured?
                Character := Player.GetFortCharacter[]
                Character.GetHealth() <= Character.GetMaxHealth() * Manager.InjuredHealthFraction
            then:
                set IsInjured = true
                Overlay.SetInjured(true)
                Manager.PlayInjured(Player)

    OnEliminated(Result:elimination_result):void =
        if (not IsDown?):
            set IsDown = true
            spawn{ Overlay.ShowSignalLost(Manager.SignalLostSeconds) }
            Manager.HandleEliminated(Player, Overlay.Callsign)

    # После долгого бега игрок тяжело дышит в микрофон камеры.
    OnSprinted(Payload:tuple(fort_character, logic)):void =
        Now := GetSimulationElapsedTime()
        if (Payload(1)?):
            set SprintStartTime = Now
        else if (not IsDown?, Now - SprintStartTime >= Manager.HeavyBreathingAfterSeconds):
            Manager.PlayBreathing(Player)
