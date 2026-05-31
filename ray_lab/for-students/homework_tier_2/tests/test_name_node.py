import time

import pytest
import ray

from src.name_node import NameNode

CONTENT = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"   # 36 znaków -> 4 chunki po 10


@pytest.fixture
def nn():
    # świeży "klaster" na każdy test -> pełna izolacja
    return NameNode.remote(num_data_nodes=4, replication=2, chunk_size=10)


def status(nn):
    return ray.get(nn.list_status.remote())


def chunks_on_all_nodes(st):
    return {c for info in st["nodes"].values() for c in info["chunks"]}


def wait_node_dead(nn, node_id, timeout=5.0):
    # wykrycie awarii jest asynchroniczne - poczekaj aż ping zacznie zawodzić
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = status(nn)
        if st["nodes"].get(node_id, {}).get("alive") is False:
            return st
        time.sleep(0.1)
    return status(nn)


def wait_node_restarted(nn, node_id, timeout=10.0):
    # po crash() Ray sam restartuje aktora (max_restarts); poczekaj aż wstanie
    from src.data_node import DataNode  # noqa: F401
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            st = ray.get(nn.list_status.remote())
            if st["nodes"].get(node_id, {}).get("alive") is True:
                return st
        except Exception:
            pass
        time.sleep(0.2)
    return ray.get(nn.list_status.remote())


# --- upload -> list ---
def test_upload_then_status(nn):
    info = ray.get(nn.upload.remote("art-1", CONTENT))
    assert info["num_chunks"] == 4

    st = status(nn)
    locs = st["artifacts"]["art-1"]
    assert len(locs) == 4
    for chunk_id, nodes in locs.items():
        assert len(set(nodes)) == 2                      # R=2 RÓŻNE kopie
    # metadane zgodne z rzeczywistością: każdy węzeł trzyma to, co metadane mówią
    for node_id, node_info in st["nodes"].items():
        for chunk_id in node_info["chunks"]:
            assert node_id in locs[chunk_id]


# --- smart update: zmiana 1 znaku w jednym chunku ---
def test_update_one_char_changes_only_one_chunk(nn):
    ray.get(nn.upload.remote("art-1", CONTENT))          # 4 chunki po 10

    # zmieniamy 1 znak w 3. chunku (indeks 20..29): 'U' -> 'X'
    new_content = CONTENT[:20] + "X" + CONTENT[21:]
    info = ray.get(nn.update.remote("art-1", new_content))

    # smart: 3 chunki bez zmian, 1 nadpisany, 0 dodanych, 0 usuniętych
    assert info == {"artifact": "art-1", "num_chunks": 4,
                    "unchanged": 3, "changed": 1, "added": 0, "removed": 0}
    assert ray.get(nn.get.remote("art-1")) == new_content

    # stan na węzłach: ID chunków nie uległy zmianie (te same art-1-0..3),
    # bo nie kasowaliśmy całego artefaktu i pisaliśmy od nowa
    st = status(nn)
    assert set(st["artifacts"]["art-1"].keys()) == {f"art-1-{i}" for i in range(4)}


# --- smart update: skrócenie artefaktu -> usuwa nadmiarowe chunki ---
def test_update_shorter_removes_tail_chunks(nn):
    ray.get(nn.upload.remote("art-1", CONTENT))          # 4 chunki
    info = ray.get(nn.update.remote("art-1", "NEW"))     # 3 znaki -> 1 chunk

    assert info["num_chunks"] == 1
    assert info["removed"] == 3                          # 3 nadmiarowe chunki usunięte
    assert ray.get(nn.get.remote("art-1")) == "NEW"

    st = status(nn)
    assert len(st["artifacts"]["art-1"]) == 1
    # stare chunki (art-1-1..art-1-3) zniknęły ze wszystkich węzłów
    assert chunks_on_all_nodes(st) == {"art-1-0"}


# --- smart update: wydłużenie -> dodaje nowe chunki ---
def test_update_longer_adds_new_chunks(nn):
    ray.get(nn.upload.remote("art-1", "SHORT"))          # 1 chunk
    info = ray.get(nn.update.remote("art-1", CONTENT))   # 36 znaków -> 4 chunki

    assert info["num_chunks"] == 4
    assert info["added"] == 3                            # 3 nowe chunki dołożone
    assert ray.get(nn.get.remote("art-1")) == CONTENT


# --- get -> list ---
def test_get_then_status(nn):
    ray.get(nn.upload.remote("art-1", CONTENT))
    assert ray.get(nn.get.remote("art-1")) == CONTENT    # złożenie chunków == oryginał
    # get nie zmienia stanu
    assert len(status(nn)["artifacts"]["art-1"]) == 4


# --- delete -> list ---
def test_delete_then_status(nn):
    ray.get(nn.upload.remote("art-1", CONTENT))
    ray.get(nn.delete.remote("art-1"))

    st = status(nn)
    assert st["artifacts"] == {}                         # brak w metadanych
    assert chunks_on_all_nodes(st) == set()              # żaden węzeł nie trzyma chunków
    with pytest.raises(Exception):                       # get usuniętego -> błąd
        ray.get(nn.get.remote("art-1"))


# --- delete node -> list (+ odzyskiwanie) ---
def test_delete_node_then_status_and_recover(nn):
    ray.get(nn.upload.remote("art-1", CONTENT))

    ray.get(nn.kill_node.remote(1))
    st = wait_node_dead(nn, 1)
    assert st["nodes"][1]["alive"] is False
    # dane dostępne MIMO awarii (czytamy z ocalałej kopii)
    assert ray.get(nn.get.remote("art-1")) == CONTENT

    result = ray.get(nn.heal.remote())
    assert result["dead_nodes"] == [1]
    assert result["lost"] == []                          # R=2 znosi 1 awarię

    st = status(nn)
    assert 1 not in st["nodes"]                          # martwy węzeł usunięty z puli
    for chunk_id, nodes in st["artifacts"]["art-1"].items():
        assert len(set(nodes)) == 2                      # znów R=2 kopie...
        assert all(st["nodes"][n]["alive"] for n in nodes)   # ...i to ŻYWE
    assert ray.get(nn.get.remote("art-1")) == CONTENT    # dane wciąż poprawne


# --- max_restarts: crash != permanent kill, Ray sam wskrzesza aktor ---
def test_data_node_auto_restart_after_crash(nn):
    ray.get(nn.upload.remote("art-1", CONTENT))

    # crash node 1 -> proces umiera, Ray restartuje aktora (max_restarts=2)
    ray.get(nn.crash_node.remote(1))
    st = wait_node_restarted(nn, 1)

    # aktor żyje (Ray go wskrzesił) ale chunki w pamięci przepadły
    assert st["nodes"][1]["alive"] is True
    assert st["nodes"][1]["chunks"] == []                # in-memory state zginął
    # mimo to dane są dostępne - czytamy z drugiego replika
    assert ray.get(nn.get.remote("art-1")) == CONTENT

    # heal wykrywa, że "żywy ale pusty" węzeł nie ma chunków z metadanych,
    # i re-replikuje na niego brakujące
    result = ray.get(nn.heal.remote())
    assert result["dead_nodes"] == []                    # nikt nie umarł na stałe
    assert len(result["re_replicated"]) > 0              # ale były re-replikacje

    st = status(nn)
    for chunk_id, nodes in st["artifacts"]["art-1"].items():
        assert len(set(nodes)) == 2                      # znów R=2
    assert ray.get(nn.get.remote("art-1")) == CONTENT
