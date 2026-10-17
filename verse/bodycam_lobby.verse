# BODYCAM для Fortnite: лобби перед матчем («Брифинг»).
#
# Игроки появляются в комнате брифинга, собирают снаряжение в арсенале и жмут «ГОТОВ».
# Матч начинается, когда готовы все (и набралось MinPlayers) или вышло MaxWaitSeconds.
# Затем короткий отсчёт, спавны лобби выключаются, и режим переносит игроков на карту.
#
# Устройство необязательное: если в нём нет ни одного спавна, режимы стартуют сразу.

using { /Fortnite.com/Devices }
using { /Fortnite.com/Characters }
using { /Fortnite.com/Playspaces }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /Verse.org/Simulation }

# Перенести игрока к спавну на карте с его поворотом.
# Встроенные устройства Fortnite не наследуются от creative_device, поэтому тип параметра — сам спавнер.
TeleportToDevice(P:player, Target:player_spawner_device):void =
    if (Character := P.GetFortCharacter[]):
        Transform := Target.GetTransform()
        if (Character.TeleportTo[Transform.Translation, Transform.Rotation]) {}

bodycam_lobby_device := class(creative_device):

    # Спавны в комнате брифинга. Включены при старте игры.
    @editable
    LobbySpawners : []player_spawner_device = array{}

    # Сколько игроков нужно для старта. Для теста в одиночку оставьте 1.
    @editable
    MinPlayers : int = 1

    # Сколько ждать неготовых, когда игроков уже хватает.
    @editable
    MaxWaitSeconds : int = 90

    @editable
    CountdownSeconds : int = 5

    # Необязательно: кнопки «Оружейный шкаф» в комнате, открывают арсенал, если меню закрыли.
    @editable
    ArsenalButtons : []button_device = array{}

    var InLobby : logic = false
    var CurrentArsenal : ?bodycam_arsenal_device = false
    var MenuTitle : string = ""

    IsConfigured()<transacts>:logic =
        if (LobbySpawners.Length > 0) then true else false

    RunLobby(Arsenal:bodycam_arsenal_device, Title:string)<suspends>:void =
        if (IsConfigured()?):
            set CurrentArsenal = option{Arsenal}
            set MenuTitle = "БРИФИНГ · {Title}"
            set InLobby = true
            Arsenal.ResetReady()
            for (Spawner : LobbySpawners):
                Spawner.Enable()
            for (Button : ArsenalButtons):
                Button.InteractedWithEvent.Subscribe(OnArsenalButton)
            GetPlayspace().PlayerAddedEvent().Subscribe(OnPlayerAdded)

            Sleep(0.5)
            for (P : GetPlayspace().GetPlayers()):
                Arsenal.OpenMenu(P, MenuTitle, true)

            # Ждём игроков и готовность.
            var Waited : int = 0
            loop:
                Players := GetPlayspace().GetPlayers()
                Count := Players.Length
                ReadyCount := Arsenal.CountReady(Players)
                if (Count >= MinPlayers, (ReadyCount >= Count or Waited >= MaxWaitSeconds)):
                    break
                if (Count < MinPlayers):
                    Arsenal.SetStatusAll("ОЖИДАНИЕ ИГРОКОВ  {Count}/{MinPlayers}")
                else:
                    Arsenal.SetStatusAll("ГОТОВЫ {ReadyCount}/{Count}  ·  СТАРТ ЧЕРЕЗ {FormatTimer(MaxWaitSeconds - Waited)}")
                    set Waited += 1
                Sleep(1.0)

            # Отсчёт перед выездом.
            var Left : int = CountdownSeconds
            loop:
                if (Left <= 0):
                    break
                Arsenal.SetStatusAll("ВЫЕЗД ЧЕРЕЗ {Left}")
                Sleep(1.0)
                set Left -= 1

            set InLobby = false
            Arsenal.CloseAll()
            for (Spawner : LobbySpawners):
                Spawner.Disable()

    OnPlayerAdded(P:player):void =
        if (InLobby?, Arsenal := CurrentArsenal?):
            Arsenal.OpenMenu(P, MenuTitle, true)

    OnArsenalButton(Agent:agent):void =
        if (InLobby?, Arsenal := CurrentArsenal?, P := player[Agent]):
            Arsenal.OpenMenu(P, MenuTitle, true)
