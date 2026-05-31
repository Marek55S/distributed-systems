import time

import pytest
import ray

from src.name_node import NameNode

CONTENT = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"   # 36 znaków -> 4 chunki po 10


@pytest.fixture
def nn():
    return NameNode.remote(num_data_nodes=4, replication=2, chunk_size=10)


def status(nn):
    return ray.get(nn.list_status.remote())


def chunks_on_all_nodes(st):
    return {c for info in st["nodes"].values() for c in info["chunks"]}


def wait_node_dead(nn, node_id, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = status(nn)
        if st["nodes"].get(node_id, {}).get("alive") is False:
            return st
        time.sleep(0.1)
    return status(nn)


def wait_node_restarted(nn, node_id, timeout=10.0):
    from src.data_node import DataNode  
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


def test_upload_then_status(nn):
    info = ray.get(nn.upload.remote("art-1", CONTENT))
    assert info["num_chunks"] == 4

    st = status(nn)
    locs = st["artifacts"]["art-1"]
    assert len(locs) == 4
    for chunk_id, nodes in locs.items():
        assert len(set(nodes)) == 2                      
    for node_id, node_info in st["nodes"].items():
        for chunk_id in node_info["chunks"]:
            assert node_id in locs[chunk_id]


def test_update_one_char_changes_only_one_chunk(nn):
    ray.get(nn.upload.remote("art-1", CONTENT))        

    new_content = CONTENT[:20] + "X" + CONTENT[21:]
    info = ray.get(nn.update.remote("art-1", new_content))

    assert info == {"artifact": "art-1", "num_chunks": 4,
                    "unchanged": 3, "changed": 1, "added": 0, "removed": 0}
    assert ray.get(nn.get.remote("art-1")) == new_content

    st = status(nn)
    assert set(st["artifacts"]["art-1"].keys()) == {f"art-1-{i}" for i in range(4)}


def test_update_shorter_removes_tail_chunks(nn):
    ray.get(nn.upload.remote("art-1", CONTENT))         
    info = ray.get(nn.update.remote("art-1", "NEW"))     

    assert info["num_chunks"] == 1
    assert info["removed"] == 3                       
    assert ray.get(nn.get.remote("art-1")) == "NEW"

    st = status(nn)
    assert len(st["artifacts"]["art-1"]) == 1
    assert chunks_on_all_nodes(st) == {"art-1-0"}


def test_update_longer_adds_new_chunks(nn):
    ray.get(nn.upload.remote("art-1", "SHORT"))         
    info = ray.get(nn.update.remote("art-1", CONTENT))  

    assert info["num_chunks"] == 4
    assert info["added"] == 3                            
    assert ray.get(nn.get.remote("art-1")) == CONTENT


def test_get_then_status(nn):
    ray.get(nn.upload.remote("art-1", CONTENT))
    assert ray.get(nn.get.remote("art-1")) == CONTENT  
    assert len(status(nn)["artifacts"]["art-1"]) == 4


def test_delete_then_status(nn):
    ray.get(nn.upload.remote("art-1", CONTENT))
    ray.get(nn.delete.remote("art-1"))

    st = status(nn)
    assert st["artifacts"] == {}                        
    assert chunks_on_all_nodes(st) == set()              
    with pytest.raises(Exception):                  
        ray.get(nn.get.remote("art-1"))


def test_delete_node_then_status_and_recover(nn):
    ray.get(nn.upload.remote("art-1", CONTENT))

    ray.get(nn.kill_node.remote(1))
    st = wait_node_dead(nn, 1)
    assert st["nodes"][1]["alive"] is False
    assert ray.get(nn.get.remote("art-1")) == CONTENT

    result = ray.get(nn.heal.remote())
    assert result["dead_nodes"] == [1]
    assert result["lost"] == []                         

    st = status(nn)
    assert 1 not in st["nodes"]                          
    for chunk_id, nodes in st["artifacts"]["art-1"].items():
        assert len(set(nodes)) == 2                    
        assert all(st["nodes"][n]["alive"] for n in nodes)   
    assert ray.get(nn.get.remote("art-1")) == CONTENT  


def test_data_node_auto_restart_after_crash(nn):
    ray.get(nn.upload.remote("art-1", CONTENT))

    ray.get(nn.crash_node.remote(1))
    st = wait_node_restarted(nn, 1)

    assert st["nodes"][1]["alive"] is True
    assert st["nodes"][1]["chunks"] == []                
    assert ray.get(nn.get.remote("art-1")) == CONTENT


    result = ray.get(nn.heal.remote())
    assert result["dead_nodes"] == []                    
    assert len(result["re_replicated"]) > 0            

    st = status(nn)
    for chunk_id, nodes in st["artifacts"]["art-1"].items():
        assert len(set(nodes)) == 2                    
    assert ray.get(nn.get.remote("art-1")) == CONTENT
