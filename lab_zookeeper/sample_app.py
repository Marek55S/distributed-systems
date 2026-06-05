"""
Przykladowa "zewnetrzna aplikacja graficzna" uruchamiana przez watcher.py,
gdy powstaje znode "/a" (i zamykana, gdy "/a" jest kasowany).

To zwykly proces potomny - dzieki temu watcher moze go niezawodnie zatrzymac
przez terminate() na KAZDEJ wersji Windows (w przeciwienstwie do notepad/mspaint
z Microsoft Store, ktore startuja jako osobny proces poza naszym uchwytem).

Mozna podstawic dowolna inna aplikacje przez opcje --app w watcher.py.
"""

import time
import tkinter as tk

root = tk.Tk()
root.title("Zewnetrzna aplikacja (znode /a istnieje)")
root.geometry("420x220")
root.configure(bg="#2e7d32")

tk.Label(
    root,
    text="Aplikacja zewnetrzna DZIALA",
    bg="#2e7d32",
    fg="white",
    font=("Segoe UI", 16, "bold"),
).pack(expand=True)
tk.Label(
    root,
    text="Uruchomiona przez watcher.py, bo powstal znode /a.\n"
    "Zostanie zamknieta, gdy /a zniknie.",
    bg="#2e7d32",
    fg="white",
    font=("Segoe UI", 10),
).pack(expand=True)

clock = tk.StringVar()
tk.Label(root, textvariable=clock, bg="#2e7d32", fg="#c8e6c9",
         font=("Consolas", 12)).pack(pady=8)


def tick():
    clock.set(time.strftime("dziala od:  %H:%M:%S"))
    root.after(1000, tick)


tick()
root.mainloop()
