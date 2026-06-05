"""
Aplikacja-obserwator dla Replicated ZooKeeper (ZooKeeper 3.8.4, klient: kazoo).

Realizuje polecenie z zadania, wykorzystujac mechanizm obserwatorow (watches):

  * gdy powstaje znode "/a"        -> uruchamiamy zewnetrzna aplikacje graficzna
                                      (komenda podana w linii polecen, opcja --app),
  * gdy "/a" jest kasowany         -> zatrzymujemy te aplikacje,
  * gdy do "/a" dodawany jest      -> pokazujemy graficzna informacje o AKTUALNEJ
    kolejny potomek                  liczbie potomkow,
  * w kazdej chwili mozna wyswietlic cala strukture drzewa "/a" (panel Treeview).

Aplikacja laczy sie z calym ensemble (--hosts), wiec dziala w srodowisku
"Replicated ZooKeeper".

------------------------------------------------------------------------------
KLUCZOWE POJECIA (dlaczego kod wyglada tak, a nie inaczej)
------------------------------------------------------------------------------
1) Watch w ZooKeeper jest JEDNORAZOWY. Po jednym powiadomieniu trzeba go ustawic
   ponownie. Biblioteka kazoo daje "przepisy" DataWatch / ChildrenWatch, ktore
   robia to automatycznie - my podajemy tylko funkcje-callback.

2) DataWatch("/a") odpala sie przy utworzeniu, zmianie danych i usunieciu wezla.
   Gdy wezel nie istnieje, callback dostaje (None, None, event). Po przejsciu
   None -> stat wiemy, ze wezel POWSTAL; po przejsciu stat -> None, ze zniknal.

3) ChildrenWatch("/a") wymaga istniejacego wezla i SAM sie zatrzymuje, gdy "/a"
   zostanie skasowany. Dlatego tworzymy go na nowo przy kazdym utworzeniu "/a".

4) Callbacki kazoo przychodza w WATKACH W TLE, a Tkinter NIE jest thread-safe.
   Dlatego callbacki tylko wrzucaja zdarzenia do kolejki (queue.Queue), a okno
   Tkinter odczytuje je w watku glownym przez root.after(). Wszystkie operacje
   na widgetach wykonujemy wylacznie w watku glownym.
"""

from __future__ import annotations

import argparse
import os
import queue
import subprocess
import sys
import time
import tkinter as tk
from tkinter import ttk

from kazoo.client import KazooClient
from kazoo.protocol.states import KazooState
from kazoo.recipe.watchers import ChildrenWatch, DataWatch


# ----------------------------------------------------------------------------
# Warstwa ZooKeeper: laczy sie z ensemble i zaklada obserwatorow.
# Nie dotyka GUI - jedynie wrzuca zdarzenia do kolejki.
# ----------------------------------------------------------------------------
class ZkObserver:
    def __init__(self, hosts: str, node: str, events: queue.Queue):
        self.node = node                  # sciezka obserwowanego wezla, np. "/a"
        self.events = events              # kolejka zdarzen do GUI
        self.zk = KazooClient(hosts=hosts)
        self._node_exists = None          # ostatni znany stan istnienia "/a"
        self._children_watch = None       # biezacy ChildrenWatch (lub None)
        self._prev_children = None        # poprzednia lista dzieci (do wykrycia "dodano")

    # --- start / stop -------------------------------------------------------
    def start(self):
        # Nasluchuj zmian stanu sesji (CONNECTED / SUSPENDED / LOST) - przyda sie
        # do pokazania w GUI, czy trzymamy lacznosc z ensemble.
        self.zk.add_listener(self._on_state)
        self.zk.start(timeout=15)
        # Glowny obserwator: istnienie i zmiany wezla "/a".
        # DataWatch sam wola callback od razu (stan poczatkowy) i przy kazdej zmianie.
        DataWatch(self.zk, self.node, self._on_node)

    def stop(self):
        try:
            self.zk.stop()
            self.zk.close()
        except Exception:
            pass

    # --- callbacki ZooKeepera (watek w tle!) --------------------------------
    def _on_state(self, state):
        self.events.put(("conn", state))

    def _on_node(self, data, stat, event=None):
        """Wolane przez DataWatch: stat=None oznacza, ze '/a' nie istnieje."""
        exists = stat is not None

        if exists and not self._node_exists:
            # Przejscie (nie istnial) -> (istnieje)  ==  UTWORZENIE "/a"
            self.events.put(("created", None))
            self._arm_children_watch()
        elif not exists and self._node_exists:
            # Przejscie (istnial) -> (nie istnieje)  ==  SKASOWANIE "/a"
            self._prev_children = None
            self._children_watch = None  # stary watch i tak sie sam zatrzymal
            self.events.put(("deleted", None))

        self._node_exists = exists

    def _arm_children_watch(self):
        """Zaklada (na nowo) obserwatora dzieci '/a'. Stary, jesli byl, jest juz martwy."""
        self._prev_children = None
        # send_event=True -> dostajemy tez obiekt zdarzenia (None przy 1. wywolaniu).
        self._children_watch = ChildrenWatch(
            self.zk, self.node, self._on_children, send_event=True
        )

    def _on_children(self, children, event=None):
        """Wolane przez ChildrenWatch przy kazdej zmianie listy dzieci '/a'."""
        count = len(children)
        prev = self._prev_children
        self._prev_children = list(children)
        # "added" = liczba dzieci wzrosla wzgledem poprzedniego stanu.
        added = prev is not None and count > len(prev)
        self.events.put(("children", {"count": count, "added": added}))

    # --- pomocnicze: zbudowanie calego drzewa "/a" --------------------------
    def build_tree(self):
        """Zwraca strukture drzewa '/a' jako zagniezdzone slowniki, albo None.

        Wolane z watku GLOWNEGO (po klliknieciu / odswiezeniu) - to zwykle,
        synchroniczne odczyty z ZooKeepera, na localhost bardzo szybkie.
        """
        if not self.zk.exists(self.node):
            return None
        return self._read_subtree(self.node)

    def _read_subtree(self, path):
        try:
            children = sorted(self.zk.get_children(path))
        except Exception:
            children = []
        return {
            "name": path.rsplit("/", 1)[-1] or "/",
            "path": path,
            "children": [
                self._read_subtree(path.rstrip("/") + "/" + c) for c in children
            ],
        }


# ----------------------------------------------------------------------------
# Warstwa GUI (Tkinter): caly kod tutaj wykonuje sie w watku glownym.
# ----------------------------------------------------------------------------
class WatcherGui:
    POLL_MS = 100              # co ile ms zagladamy do kolejki zdarzen
    _BANNER_IDLE_BG = "#eceff1"  # neutralne tlo paska powiadomien

    def __init__(self, root: tk.Tk, observer: ZkObserver, app_cmd: str,
                 launch_app: bool = True):
        self.root = root
        self.obs = observer
        self.app_cmd = app_cmd          # komenda zewnetrznej aplikacji graficznej
        self.launch_app = launch_app    # czy w ogole uruchamiac apke zewnetrzna (--no-app)
        self.ext_proc: subprocess.Popen | None = None  # uchwyt do tej aplikacji
        self._banner_after = None       # id zaplanowanego resetu paska powiadomien

        root.title(f"ZooKeeper watcher  -  obserwowany wezel: {observer.node}")
        root.geometry("720x640")
        self._build_widgets()

        # Uruchom petle odpytywania kolejki zdarzen.
        self.root.after(self.POLL_MS, self._drain_events)
        # Posprzataj przy zamknieciu okna.
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # --- budowa interfejsu --------------------------------------------------
    def _build_widgets(self):
        pad = {"padx": 8, "pady": 4}

        # Pasek stanu: polaczenie + istnienie "/a".
        top = ttk.Frame(self.root)
        top.pack(fill="x", **pad)
        self.conn_var = tk.StringVar(value="laczenie...")
        self.node_var = tk.StringVar(value="?")
        ttk.Label(top, text="Ensemble:").grid(row=0, column=0, sticky="w")
        self.conn_lbl = ttk.Label(top, textvariable=self.conn_var, foreground="gray")
        self.conn_lbl.grid(row=0, column=1, sticky="w", padx=(4, 20))
        ttk.Label(top, text=f"Wezel {self.obs.node}:").grid(row=0, column=2, sticky="w")
        self.node_lbl = ttk.Label(top, textvariable=self.node_var, foreground="gray")
        self.node_lbl.grid(row=0, column=3, sticky="w", padx=4)

        # Duzy licznik potomkow + stan aplikacji zewnetrznej.
        mid = ttk.Frame(self.root)
        mid.pack(fill="x", **pad)
        ttk.Label(mid, text="Liczba potomkow:").pack(side="left")
        self.count_var = tk.StringVar(value="-")
        ttk.Label(mid, textvariable=self.count_var, font=("Segoe UI", 28, "bold")).pack(
            side="left", padx=12
        )
        self.app_var = tk.StringVar(
            value=("apka zewn.: wylaczona (--no-app)" if not self.launch_app
                   else "apka zewn.: niewystartowana")
        )
        ttk.Label(mid, textvariable=self.app_var).pack(side="right")

        # Pasek powiadomien - zastepuje wyskakujace okienka. Zmienia tresc i kolor
        # w MIEJSCU (jedno okno GUI) i sam wraca do stanu neutralnego.
        self.banner_var = tk.StringVar(value="czekam na zdarzenia...")
        self.banner = tk.Label(
            self.root, textvariable=self.banner_var, anchor="center", height=2,
            font=("Segoe UI", 13, "bold"), bg=self._BANNER_IDLE_BG, fg="#333333",
        )
        self.banner.pack(fill="x", padx=8, pady=4)

        # Drzewo struktury "/a".
        tree_frame = ttk.LabelFrame(self.root, text=f"Struktura drzewa {self.obs.node}")
        tree_frame.pack(fill="both", expand=True, **pad)
        self.tree = ttk.Treeview(tree_frame, show="tree")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        ttk.Button(self.root, text="Odswiez drzewo", command=self.refresh_tree).pack(
            anchor="w", padx=8
        )

        # Log zdarzen.
        log_frame = ttk.LabelFrame(self.root, text="Log zdarzen")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log = tk.Text(log_frame, height=8, state="disabled", wrap="word")
        self.log.pack(side="left", fill="both", expand=True)
        lsb = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        lsb.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=lsb.set)

    # --- petla odbioru zdarzen z ZooKeepera ---------------------------------
    def _drain_events(self):
        try:
            while True:
                kind, payload = self.obs.events.get_nowait()
                self._handle(kind, payload)
        except queue.Empty:
            pass
        # Zaplanuj kolejne zajrzenie do kolejki.
        self.root.after(self.POLL_MS, self._drain_events)

    def _handle(self, kind, payload):
        if kind == "conn":
            self._on_conn(payload)
        elif kind == "created":
            self._on_created()
        elif kind == "deleted":
            self._on_deleted()
        elif kind == "children":
            self._on_children(payload)

    # --- reakcje na poszczegolne zdarzenia ----------------------------------
    def _on_conn(self, state):
        if state == KazooState.CONNECTED:
            self.conn_var.set("polaczono")
            self.conn_lbl.configure(foreground="green")
        elif state == KazooState.SUSPENDED:
            self.conn_var.set("zawieszone (utrata polaczenia z wezlem)")
            self.conn_lbl.configure(foreground="orange")
        else:  # LOST
            self.conn_var.set("sesja utracona")
            self.conn_lbl.configure(foreground="red")
        self._log(f"[sesja] {state}")

    def _on_created(self):
        self.node_var.set("ISTNIEJE")
        self.node_lbl.configure(foreground="green")
        self._log(f"Utworzono {self.obs.node}")
        self._start_external_app()
        self.count_var.set("0")
        self.refresh_tree()
        self._notify(f"Utworzono {self.obs.node}", "#2e7d32", "white")

    def _on_deleted(self):
        self.node_var.set("nie istnieje")
        self.node_lbl.configure(foreground="red")
        self._log(f"Skasowano {self.obs.node}  ->  zatrzymuje aplikacje zewnetrzna")
        self._stop_external_app()
        self.count_var.set("-")
        self.refresh_tree()
        self._notify(f"Skasowano {self.obs.node} - zatrzymano aplikacje", "#c62828", "white")

    def _on_children(self, info):
        count = info["count"]
        self.count_var.set(str(count))
        self.refresh_tree()
        if info["added"]:
            self._log(f"Dodano potomka. Aktualna liczba potomkow: {count}")
            self._notify(f"Dodano potomka!  Aktualna liczba potomkow: {count}",
                         "#1e88e5", "white")
        else:
            self._log(f"Zmiana listy potomkow. Aktualna liczba: {count}")

    # --- pasek powiadomien (w jednym oknie, zamiast popupow) ----------------
    def _notify(self, msg, bg="#1e88e5", fg="white"):
        """Pokaz komunikat w pasku i po ~3 s wroc do stanu neutralnego."""
        self.banner_var.set(msg)
        self.banner.configure(bg=bg, fg=fg)
        if self._banner_after is not None:
            self.root.after_cancel(self._banner_after)
        self._banner_after = self.root.after(3000, self._banner_reset)

    def _banner_reset(self):
        self.banner.configure(bg=self._BANNER_IDLE_BG, fg="#333333")
        self._banner_after = None

    # --- zewnetrzna aplikacja graficzna -------------------------------------
    def _start_external_app(self):
        if not self.launch_app:
            self._log("   (--no-app: pomijam uruchomienie aplikacji zewnetrznej)")
            return
        if self.ext_proc is not None and self.ext_proc.poll() is None:
            return  # juz dziala - nie uruchamiamy drugiej kopii
        try:
            # Na Windows Popen przyjmuje komende jako string i przekazuje do
            # CreateProcess - dziala dla "notepad", "mspaint", "<exe> <skrypt>".
            self.ext_proc = subprocess.Popen(self.app_cmd)
            self.app_var.set(f"apka zewn.: dziala (PID {self.ext_proc.pid})")
            self._log(f"   uruchomiono aplikacje zewnetrzna (PID {self.ext_proc.pid})")
        except Exception as exc:
            self._log(f"   BLAD uruchomienia aplikacji: {exc}")
            self.app_var.set("apka zewn.: blad uruchomienia")
            self.ext_proc = None

    def _stop_external_app(self):
        if self.ext_proc is None:
            self.app_var.set("apka zewn.: niewystartowana")
            return
        if self.ext_proc.poll() is None:  # nadal dziala
            try:
                self.ext_proc.terminate()
                try:
                    self.ext_proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.ext_proc.kill()
                self._log("   aplikacja zewnetrzna zatrzymana")
            except Exception as exc:
                self._log(f"   BLAD zatrzymania aplikacji: {exc}")
        self.ext_proc = None
        self.app_var.set("apka zewn.: zatrzymana")

    # --- drzewo -------------------------------------------------------------
    def refresh_tree(self):
        # Wyczysc i odbuduj widok drzewa od korzenia "/a".
        for item in self.tree.get_children(""):
            self.tree.delete(item)
        tree = self.obs.build_tree()
        if tree is None:
            self.tree.insert("", "end", text=f"{self.obs.node} (nie istnieje)")
            return
        self._insert_node("", tree)

    def _insert_node(self, parent_id, node):
        label = node["name"]
        if node["children"]:
            label += f"  ({len(node['children'])})"
        item_id = self.tree.insert(parent_id, "end", text=label, open=True)
        for child in node["children"]:
            self._insert_node(item_id, child)

    # --- log ----------------------------------------------------------------
    def _log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.log.configure(state="normal")
        self.log.insert("end", f"{ts}  {msg}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    # --- zamkniecie ---------------------------------------------------------
    def _on_close(self):
        self._stop_external_app()
        self.obs.stop()
        self.root.destroy()


def _default_app_cmd():
    """Domyslna aplikacja zewnetrzna: dolaczony sample_app.py (jedno, zamykalne okno).

    Uruchamiamy go tym samym interpreterem co watcher; jesli obok python.exe jest
    pythonw.exe, uzywamy pythonw, zeby nie migalo dodatkowe okno konsoli.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pyw):
        exe = pyw
    return f'"{exe}" "{os.path.join(here, "sample_app.py")}"'


def main():
    parser = argparse.ArgumentParser(
        description="ZooKeeper watcher z GUI (kazoo + Tkinter)."
    )
    parser.add_argument(
        "--hosts",
        default="localhost:2181,localhost:2182,localhost:2183",
        help="Lista wezlow ensemble (domyslnie 3-wezlowy Replicated ZooKeeper).",
    )
    parser.add_argument(
        "--node", default="/a", help="Sciezka obserwowanego wezla (domyslnie /a)."
    )
    parser.add_argument(
        "--app",
        default=_default_app_cmd(),
        help="Komenda zewnetrznej aplikacji graficznej (domyslnie dolaczony "
        'sample_app.py). Mozna podac np. "mspaint".',
    )
    parser.add_argument(
        "--no-app",
        action="store_true",
        help="Nie uruchamiaj aplikacji zewnetrznej - tylko jedno okno GUI watchera.",
    )
    args = parser.parse_args()

    events: queue.Queue = queue.Queue()
    observer = ZkObserver(args.hosts, args.node, events)
    try:
        observer.start()
    except Exception as exc:
        print(f"Nie udalo sie polaczyc z ensemble ({args.hosts}): {exc}")
        sys.exit(1)

    root = tk.Tk()
    WatcherGui(root, observer, args.app, launch_app=not args.no_app)
    root.mainloop()


if __name__ == "__main__":
    main()
