@echo off
REM Otwiera trzy osobne okna konsoli - po jednym na kazdy wezel ensemble.
REM Kazdy wezel poczeka az wstanie quorum (potrzebne min. 2 z 3 wezlow).
setlocal
start "ZooKeeper node 1" cmd /k "%~dp0start_node.cmd" 1
start "ZooKeeper node 2" cmd /k "%~dp0start_node.cmd" 2
start "ZooKeeper node 3" cmd /k "%~dp0start_node.cmd" 3
echo Uruchomiono 3 wezly w osobnych oknach.
echo Klienci lacza sie pod: localhost:2181,localhost:2182,localhost:2183
endlocal
