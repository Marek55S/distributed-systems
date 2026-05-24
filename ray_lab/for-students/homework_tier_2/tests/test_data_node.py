import ray

from src.data_node import DataNode


def test_store_and_get():
    node = DataNode.remote(0)
    assert ray.get(node.store.remote("c0", "Hello")) is True
    assert ray.get(node.get.remote("c0")) == "Hello"


def test_get_missing_returns_none():
    node = DataNode.remote(1)
    assert ray.get(node.get.remote("nie-ma")) is None


def test_delete_is_idempotent():
    node = DataNode.remote(2)
    ray.get(node.store.remote("c0", "x"))
    assert ray.get(node.delete.remote("c0")) is True
    assert ray.get(node.delete.remote("c0")) is True  
    assert ray.get(node.get.remote("c0")) is None


def test_list_and_status():
    node = DataNode.remote(3)
    ray.get(node.store.remote("a", "1"))
    ray.get(node.store.remote("b", "2"))
    assert set(ray.get(node.list_chunks.remote())) == {"a", "b"}

    st = ray.get(node.status.remote())
    assert st["node_id"] == 3
    assert st["num_chunks"] == 2
    assert set(st["chunk_ids"]) == {"a", "b"}
