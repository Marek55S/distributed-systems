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


# --- update -> list ---
def test_update_then_status(nn):
    ray.get(nn.upload.remote("art-1", CONTENT))
    ray.get(nn.update.remote("art-1", "NEW"))            # 3 znaki -> 1 chunk

    assert ray.get(nn.get.remote("art-1")) == "NEW"
    st = status(nn)
    assert len(st["artifacts"]["art-1"]) == 1
    # stare chunki (art-1-1..art-1-3) zniknęły ze wszystkich węzłów
    assert chunks_on_all_nodes(st) == {"art-1-0"}


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
