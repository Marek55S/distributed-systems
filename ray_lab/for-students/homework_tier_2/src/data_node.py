import ray

@ray.remote
class DataNode:
    def __init__(self,node_id):
        self.node_id = node_id
        self.chunks = {}
    
    def store(self, chunk_id, data):
        self.chunks[chunk_id] = data
        return True
    
    def get(self, chunk_id):
        return self.chunks.get(chunk_id, None)
    
    def delete(self, chunk_id):
        self.chunks.pop(chunk_id, None)
        return True
    
    def list_chunks(self):
        return list(self.chunks.keys())
    
    def ping(self):
        return self.node_id
    
    def status(self):
        return {
            'node_id': self.node_id,
            'num_chunks': len(self.chunks),
            'chunk_ids': list(self.chunks.keys())
        }

    def location(self):
        import socket
        return {
            'node_id': self.node_id,
            'ray_node': ray.get_runtime_context().get_node_id()[:12],
            'host': socket.gethostname(),
        }

if __name__ == "__main__":
    nodes = [DataNode.remote(i) for i in range(3)]

    ray.get(nodes[0].store.remote("art-1-0", "Hello"))
    ray.get(nodes[0].store.remote("art-1-1", "World"))

    print(ray.get(nodes[0].get.remote("art-1-0")))      
    print(ray.get(nodes[0].get.remote("nieistnieje")))  

    print(ray.get(nodes[0].list_chunks.remote()))     

    ray.get(nodes[0].delete.remote("art-1-0"))
    print(ray.get(nodes[0].list_chunks.remote()))      

    for n in nodes:
        print(ray.get(n.status.remote()))

    print("ping node 1 ->", ray.get(nodes[1].ping.remote()))  