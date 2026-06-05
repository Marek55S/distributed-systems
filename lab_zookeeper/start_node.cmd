@echo off
REM Uruchamia pojedynczy wezel ensemble.  Uzycie:  start_node.cmd 1   (albo 2, 3)
REM Wola QuorumPeerMain bezposrednio ze wskazanym plikiem konfiguracyjnym,
REM dzieki czemu omijamy zkEnv.cmd, ktore na sztywno ustawia ZOOCFG=conf\zoo.cfg.
setlocal
if "%~1"=="" (
  echo Uzycie: start_node.cmd ^<numer-wezla 1^|2^|3^>
  exit /b 1
)
set N=%~1
set DIST=%~dp0apache-zookeeper-3.8.4-bin
set CLASSPATH=%DIST%\*;%DIST%\lib\*;%DIST%\conf
title ZooKeeper node %N%
java "-Dzookeeper.log.dir=%DIST%\logs" "-Dzookeeper.log.file=zookeeper-node%N%.log" -cp "%CLASSPATH%" org.apache.zookeeper.server.quorum.QuorumPeerMain "%DIST%\conf\zoo_%N%.cfg"
endlocal
