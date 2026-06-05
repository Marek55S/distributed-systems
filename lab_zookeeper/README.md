# Lab ZooKeeper — obserwator znode `/a` (Replicated ZooKeeper + watches)

Aplikacja w Pythonie (klient **kazoo**, GUI **Tkinter**) realizująca polecenie:

- gdy powstaje znode **`a`** → uruchamiana jest **zewnętrzna aplikacja graficzna**
  (dowolna, podana w linii poleceń opcją `--app`),
- gdy `a` jest **kasowany** → ta aplikacja jest **zatrzymywana**,
- każde **dodanie potomka** do `a` → w głównym oknie pojawia się **graficzna
  informacja o aktualnej liczbie potomków** (pasek powiadomień + duży licznik na żywo;
  bez osobnych wyskakujących okienek),
- w dowolnej chwili można zobaczyć **całą strukturę drzewa `a`** (panel *Treeview*),
- całość działa w środowisku **Replicated ZooKeeper** (ensemble 3 węzłów).

ZooKeeper 3.8.4 API: https://zookeeper.apache.org/doc/r3.8.4/apidocs/zookeeper-server/index.html

## Pliki

| Plik | Rola |
|------|------|
| `watcher.py` | główna aplikacja — obserwatorzy (`DataWatch`, `ChildrenWatch`) + GUI |
| `zk_helper.py` | osobny klient do demonstracji: tworzy/kasuje `/a`, dodaje potomków |
| `sample_app.py` | przykładowa „zewnętrzna aplikacja graficzna” (okno Tkinter) |
| `apache-zookeeper-3.8.4-bin/conf/zoo_1.cfg`, `zoo_2.cfg`, `zoo_3.cfg` | konfiguracje 3 węzłów |
| `data/1/myid`, `data/2/myid`, `data/3/myid` | identyfikatory węzłów (1, 2, 3) |
| `start_node.cmd` | uruchamia jeden węzeł ensemble: `start_node.cmd 1\|2\|3` |
| `start_ensemble.cmd` | uruchamia od razu wszystkie 3 węzły w osobnych oknach |

## Konfiguracja Replicated ZooKeeper

Trzy węzły na jednej maszynie, każdy z własnymi portami i katalogiem danych:

| Węzeł | clientPort | kworum | elekcja | AdminServer | dataDir |
|------:|:----------:|:------:|:-------:|:-----------:|---------|
| 1 | 2181 | 2888 | 3888 | 8081 | `data/1` |
| 2 | 2182 | 2889 | 3889 | 8082 | `data/2` |
| 3 | 2183 | 2890 | 3890 | 8083 | `data/3` |

Wspólny skład ensemble w każdym pliku `zoo_N.cfg`:

```
server.1=localhost:2888:3888
server.2=localhost:2889:3889
server.3=localhost:2890:3890
```

Do działania quorum wystarczą **2 z 3** węzłów (można jeden ubić — usługa działa dalej).

> Uwaga: skrypty `start_node.cmd` wołają `QuorumPeerMain` wprost ze wskazanym
> plikiem konfiguracyjnym. Standardowy `zkServer.cmd` tego nie umożliwia, bo
> `zkEnv.cmd` na sztywno ustawia `ZOOCFG=conf\zoo.cfg`.

## Uruchomienie (Windows, PowerShell)

### 1. Wystartuj ensemble (3 węzły)

```powershell
cd lab_zookeeper
.\start_ensemble.cmd          # otworzy 3 okna konsoli (po jednym na węzeł)
```

Po kilku sekundach klienci łączą się pod `localhost:2181,localhost:2182,localhost:2183`.

### 2. Uruchom aplikację-obserwatora

Najprościej — domyślnie uruchamia dołączony `sample_app.py` (jedno, **zamykalne** okno):

```powershell
# z katalogu projektu (rozprochy)
uv run lab_zookeeper/watcher.py
```

Inna aplikacja zewnętrzna (np. systemowa):

```powershell
uv run lab_zookeeper/watcher.py --app mspaint
```

Tylko jedno okno GUI watchera, bez żadnej aplikacji zewnętrznej:

```powershell
uv run lab_zookeeper/watcher.py --no-app
```

Opcje: `--hosts` (lista węzłów), `--node` (domyślnie `/a`),
`--app` (komenda aplikacji, domyślnie `sample_app.py`), `--no-app` (nie uruchamiaj apki).

### 3. Wywołuj zmiany innym klientem (osobne okno)

```powershell
uv run lab_zookeeper/zk_helper.py create        # tworzy /a   -> watcher uruchamia aplikację
uv run lab_zookeeper/zk_helper.py add           # dodaje potomka (sekwencyjny childN) -> okienko z liczbą
uv run lab_zookeeper/zk_helper.py add --name x  # dodaje potomka /a/x
uv run lab_zookeeper/zk_helper.py tree          # drukuje drzewo /a w konsoli
uv run lab_zookeeper/zk_helper.py delete        # kasuje /a   -> watcher zatrzymuje aplikację
uv run lab_zookeeper/zk_helper.py demo          # automatyczny mini-scenariusz
```

Można też użyć dołączonego klienta CLI ZooKeepera:
`apache-zookeeper-3.8.4-bin\bin\zkCli.cmd -server localhost:2181`.

## Ważne: wybór „zewnętrznej aplikacji graficznej”

`watcher` uruchamia aplikację przez `subprocess.Popen` i zatrzymuje ją przez
`terminate()`. Działa to niezawodnie, gdy uruchamiany proces **jest** tym, który
chcemy ubić — dlatego **domyślną** aplikacją jest dołączony `sample_app.py`
(uruchamiany przez `pythonw.exe` z venv): otwiera się przy `create /a` i znika
przy `delete /a`.

Na **Windows 11** `notepad` i (część wersji) `mspaint` to aplikacje z Microsoft
Store: komenda uruchamia jedynie *stub*, a właściwe okno startuje jako osobny proces
poza naszym uchwytem — wtedy aplikacja **wystartuje, ale nie da się jej automatycznie
zamknąć** (a kolejne `create` mnożą okna). Dlatego do pełnego demo (uruchom **i**
zatrzymaj) używaj domyślnego `sample_app.py` albo innego klasycznego programu Win32.

## Jak to działa (mechanizm watches)

- **`DataWatch("/a")`** — żyje przez cały czas, przeżywa reconnect. Gdy węzeł nie
  istnieje, callback dostaje `(None, None)`. Przejście `None → stat` = utworzenie
  `/a` (start aplikacji); `stat → None` = skasowanie `/a` (stop aplikacji).
- **`ChildrenWatch("/a")`** — reaguje na zmiany listy potomków. Wymaga istniejącego
  węzła i **sam się zatrzymuje**, gdy `/a` zostanie skasowany; dlatego `watcher`
  zakłada go na nowo przy każdym utworzeniu `/a`.
- Watch w ZooKeeper jest **jednorazowy** — kazoo (recipes) automatycznie odnawia
  rejestrację po każdym powiadomieniu.
- Callbacki przychodzą w **wątkach w tle**, a Tkinter nie jest thread-safe, więc
  trafiają najpierw do `queue.Queue`, a GUI czyta je w wątku głównym przez `root.after()`.

## Zatrzymanie

Zamknij okno aplikacji-obserwatora oraz okna konsoli węzłów ensemble. Awaryjnie:

```powershell
Get-Process java -ErrorAction SilentlyContinue | Stop-Process -Force
```
