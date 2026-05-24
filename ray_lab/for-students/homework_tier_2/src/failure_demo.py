import ray

from src.name_node import NameNode


def show(nn, title):
    st = ray.get(nn.list_status.remote())
    print(f"\n \t {title} \t")
    for nid, info in st["nodes"].items():
        print(f"  node {nid}: alive={info['alive']} chunks={info['chunks']}")
    print("  locations:", st["artifacts"].get("art-1"))


if __name__ == "__main__":
    ray.init(ignore_reinit_error=True)

    nn = NameNode.remote(num_data_nodes=4, replication=2, chunk_size=10)
    content = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    ray.get(nn.upload.remote("art-1", content))
    show(nn, "after upload")

    print("\nkill node 1 ->", ray.get(nn.kill_node.remote(1)))
    show(nn, "after failure")

    print("\nget after failure OK:", ray.get(nn.get.remote("art-1")) == content)

    print("\nheal ->", ray.get(nn.heal.remote()))
    show(nn, "after heal")

    print("\nget after heal OK:", ray.get(nn.get.remote("art-1")) == content)

    ray.shutdown()
