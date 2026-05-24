import ray
from ray.exceptions import RayActorError

from src.data_node import DataNode


@ray.remote
class NameNode:

    def __init__(self, num_data_nodes=4, replication=2, chunk_size=20):
        assert replication <= num_data_nodes, "replication must be <= num_data_nodes"
        self.replication = replication
        self.chunk_size = chunk_size
        self.data_nodes = {i: DataNode.remote(i) for i in range(num_data_nodes)}
        self.artifacts = {}         
        self.chunk_locations = {}   

    def _split(self, content):
        return [content[i:i + self.chunk_size]
                for i in range(0, len(content), self.chunk_size)]

    def _pick_replicas(self, chunk_index):
        node_ids = sorted(self.data_nodes.keys())
        n = len(node_ids)
        return [node_ids[(chunk_index + r) % n] for r in range(self.replication)]

    def _read_chunk(self, chunk_id):
        for node_id in self.chunk_locations[chunk_id]:
            node = self.data_nodes.get(node_id)
            if node is None:
                continue
            try:
                data = ray.get(node.get.remote(chunk_id))
                if data is not None:
                    return data
            except RayActorError:
                continue                
        raise RuntimeError(f"Chunk {chunk_id} is unavailable (all replicas failed)")

    def _write(self, name, content):
        chunk_ids = []
        for idx, chunk_data in enumerate(self._split(content)):
            chunk_id = f"{name}-{idx}"
            replicas = self._pick_replicas(idx)
            ray.get([self.data_nodes[n].store.remote(chunk_id, chunk_data) for n in replicas])
            self.chunk_locations[chunk_id] = replicas
            chunk_ids.append(chunk_id)
        self.artifacts[name] = chunk_ids

    def _remove_chunks(self, name):
        for chunk_id in self.artifacts[name]:
            for node_id in self.chunk_locations[chunk_id]:
                node = self.data_nodes.get(node_id)
                if node is None:
                    continue
                try:
                    ray.get(node.delete.remote(chunk_id))
                except RayActorError:
                    continue
            del self.chunk_locations[chunk_id]

    def upload(self, name, content):
        if name in self.artifacts:
            raise ValueError(f"Artifact '{name}' already exists (use update)")
        self._write(name, content)
        return {"artifact": name, "num_chunks": len(self.artifacts[name])}

    def update(self, name, content):
        if name not in self.artifacts:
            raise KeyError(f"Artifact '{name}' does not exist (use upload)")
        self._remove_chunks(name)
        self._write(name, content)
        return {"artifact": name, "num_chunks": len(self.artifacts[name])}

    def delete(self, name):
        if name not in self.artifacts:
            raise KeyError(f"Artifact '{name}' does not exist")
        self._remove_chunks(name)
        del self.artifacts[name]
        return {"artifact": name, "deleted": True}

    def get(self, name):
        if name not in self.artifacts:
            raise KeyError(f"Artifact '{name}' does not exist")
        parts = [self._read_chunk(cid) for cid in self.artifacts[name]]
        return "".join(parts)

    def get_locations(self, name):
        return {cid: self.chunk_locations[cid] for cid in self.artifacts[name]}

    def list_status(self):
        nodes = {}
        for node_id, node in self.data_nodes.items():
            try:
                ray.get(node.ping.remote())
                nodes[node_id] = {"alive": True,
                                  "chunks": sorted(ray.get(node.list_chunks.remote()))}
            except RayActorError:
                nodes[node_id] = {"alive": False, "chunks": []}

        artifacts = {
            name: {cid: self.chunk_locations[cid] for cid in chunk_ids}
            for name, chunk_ids in self.artifacts.items()
        }
        return {"replication": self.replication,
                "num_nodes": len(self.data_nodes),
                "nodes": nodes,
                "artifacts": artifacts}

    def where_are_nodes(self):
        return {nid: ray.get(node.location.remote())
                for nid, node in self.data_nodes.items()}

    def kill_node(self, node_id):
        ray.kill(self.data_nodes[node_id])
        return {"killed": node_id}

    def add_node(self):
        new_id = (max(self.data_nodes) + 1) if self.data_nodes else 0
        self.data_nodes[new_id] = DataNode.remote(new_id)
        return {"added": new_id}

    def _dead_nodes(self):
        dead = []
        for node_id, node in self.data_nodes.items():
            try:
                ray.get(node.ping.remote())
            except RayActorError:
                dead.append(node_id)
        return dead

    def heal(self):
        dead = self._dead_nodes()
        for node_id in dead:
            del self.data_nodes[node_id]

        re_replicated = []
        lost = []
        for chunk_id, locations in self.chunk_locations.items():
            live = [n for n in locations if n in self.data_nodes]
            self.chunk_locations[chunk_id] = live
            if not live:
                lost.append(chunk_id)        
                continue
            while len(self.chunk_locations[chunk_id]) < self.replication:
                candidates = [n for n in self.data_nodes
                              if n not in self.chunk_locations[chunk_id]]
                if not candidates:
                    break                     
                source = self.chunk_locations[chunk_id][0]
                data = ray.get(self.data_nodes[source].get.remote(chunk_id))
                target = candidates[0]
                ray.get(self.data_nodes[target].store.remote(chunk_id, data))
                self.chunk_locations[chunk_id].append(target)
                re_replicated.append((chunk_id, target))
        return {"dead_nodes": dead, "re_replicated": re_replicated, "lost": lost}


if __name__ == "__main__":
    ray.init(ignore_reinit_error=True)

    nn = NameNode.remote(num_data_nodes=4, replication=2, chunk_size=10)
    content = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"     

    print("upload:", ray.get(nn.upload.remote("art-1", content)))
    print("locations:", ray.get(nn.get_locations.remote("art-1")))

    got = ray.get(nn.get.remote("art-1"))
    print("round-trip OK:", got == content)
    print("content:", got)

    print("update:", ray.get(nn.update.remote("art-1", "SHORT-CONTENT")))
    print("after update:", ray.get(nn.get.remote("art-1")))

    status = ray.get(nn.list_status.remote())
    print("status:")
    for node_id, info in status["nodes"].items():
        print(f"  node {node_id}: alive={info['alive']} chunks={info['chunks']}")
    print("  artifacts:", status["artifacts"])

    print("delete:", ray.get(nn.delete.remote("art-1")))
    print("artifacts after delete:", ray.get(nn.list_status.remote())["artifacts"])

    ray.shutdown()
