"""
Pomocniczy klient ZooKeeper - OSOBNY proces, ktory zmienia stan drzewa.

Sluzy do demonstracji: to on tworzy/kasuje "/a" oraz dodaje potomkow, a
aplikacja watcher.py (uruchomiona obok) reaguje na te zmiany przez obserwatorow.
Dziala na tym samym ensemble (Replicated ZooKeeper).

Uzycie (z katalogu projektu, przez uv):
    uv run lab_zookeeper/zk_helper.py create            # utworz /a
    uv run lab_zookeeper/zk_helper.py add               # dodaj kolejnego potomka /a/childN
    uv run lab_zookeeper/zk_helper.py add --name foo    # dodaj potomka /a/foo
    uv run lab_zookeeper/zk_helper.py rm-child foo      # usun potomka /a/foo
    uv run lab_zookeeper/zk_helper.py delete            # usun /a (rekurencyjnie)
    uv run lab_zookeeper/zk_helper.py tree              # wypisz drzewo /a w konsoli
    uv run lab_zookeeper/zk_helper.py demo              # mini-scenariusz pokazowy
"""

from __future__ import annotations

import argparse
import time

from kazoo.client import KazooClient
from kazoo.exceptions import NodeExistsError, NoNodeError

DEFAULT_HOSTS = "localhost:2181,localhost:2182,localhost:2183"
NODE = "/a"


def connect(hosts: str) -> KazooClient:
    zk = KazooClient(hosts=hosts)
    zk.start(timeout=15)
    return zk


def cmd_create(zk):
    try:
        zk.create(NODE, b"root-a")
        print(f"utworzono {NODE}")
    except NodeExistsError:
        print(f"{NODE} juz istnieje")


def cmd_delete(zk):
    try:
        zk.delete(NODE, recursive=True)
        print(f"usunieto {NODE} (rekurencyjnie)")
    except NoNodeError:
        print(f"{NODE} nie istnieje")


def cmd_add(zk, name: str | None):
    if not zk.exists(NODE):
        print(f"{NODE} nie istnieje - najpierw 'create'")
        return
    if name:
        path = f"{NODE}/{name}"
        zk.create(path, b"child")
        print(f"dodano potomka {path}")
    else:
        # Wezel sekwencyjny: ZooKeeper sam nadaje rosnacy numer w nazwie.
        path = zk.create(f"{NODE}/child", b"child", sequence=True)
        print(f"dodano potomka {path}")


def cmd_rm_child(zk, name: str):
    path = f"{NODE}/{name}"
    try:
        zk.delete(path, recursive=True)
        print(f"usunieto {path}")
    except NoNodeError:
        print(f"{path} nie istnieje")


def cmd_tree(zk):
    if not zk.exists(NODE):
        print(f"{NODE} nie istnieje")
        return
    _print_tree(zk, NODE, "")


def _print_tree(zk, path, prefix):
    name = path.rsplit("/", 1)[-1] or "/"
    print(f"{prefix}{name}")
    children = sorted(zk.get_children(path))
    for i, c in enumerate(children):
        last = i == len(children) - 1
        branch = "    " if last else "|   "
        _print_tree(zk, path.rstrip("/") + "/" + c, prefix + branch)


def cmd_demo(zk):
    """Krotki scenariusz: utworz /a, dodaj 3 potomkow, pokaz drzewo, posprzataj."""
    print("== DEMO ==")
    cmd_create(zk)
    time.sleep(1.5)
    for _ in range(3):
        cmd_add(zk, None)
        time.sleep(1.5)
    cmd_tree(zk)
    print("(za 3 s skasuje /a)")
    time.sleep(3)
    cmd_delete(zk)


def main():
    p = argparse.ArgumentParser(description="Pomocniczy klient ZooKeeper do demo.")
    p.add_argument("--hosts", default=DEFAULT_HOSTS)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("create")
    sub.add_parser("delete")
    a = sub.add_parser("add")
    a.add_argument("--name", default=None, help="nazwa potomka (domyslnie sekwencyjny childN)")
    r = sub.add_parser("rm-child")
    r.add_argument("name", help="nazwa potomka do usuniecia")
    sub.add_parser("tree")
    sub.add_parser("demo")
    args = p.parse_args()

    zk = connect(args.hosts)
    try:
        if args.command == "create":
            cmd_create(zk)
        elif args.command == "delete":
            cmd_delete(zk)
        elif args.command == "add":
            cmd_add(zk, args.name)
        elif args.command == "rm-child":
            cmd_rm_child(zk, args.name)
        elif args.command == "tree":
            cmd_tree(zk)
        elif args.command == "demo":
            cmd_demo(zk)
    finally:
        zk.stop()
        zk.close()


if __name__ == "__main__":
    main()
