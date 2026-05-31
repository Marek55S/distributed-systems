import ray

from src.name_node import NameNode

CONTENT = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


if __name__ == "__main__":
    ray.init(address="auto")

    print("=== Ray cluster nodes ===")
    for node in ray.nodes():
        print(f"  ray_node={node['NodeID'][:12]}  alive={node['Alive']}  "
              f"addr={node['NodeManagerAddress']}  CPU={node['Resources'].get('CPU')}")
    print("cluster CPUs:", ray.cluster_resources().get("CPU"))

    nn = NameNode.remote(num_data_nodes=4, replication=2, chunk_size=10)
    print("\nupload:", ray.get(nn.upload.remote("art-1", CONTENT)))

    print("\n=== gdzie siedzą DataNode'y (fizyczne węzły klastra) ===")
    for nid, loc in ray.get(nn.where_are_nodes.remote()).items():
        print(f"  DataNode {nid} -> ray_node={loc['ray_node']} host={loc['host']}")

    print("\nget OK:", ray.get(nn.get.remote("art-1")) == CONTENT)

    ray.shutdown()
