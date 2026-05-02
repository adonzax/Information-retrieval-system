"""
HITS Algorithm on Cranfield Citation Graph
Uses the citation graph from linkgraph.txt (no Elasticsearch needed!)
"""
import math
from collections import defaultdict

def load_graph(graph_file):
    """Load citation graph from file"""
    link_graph = {}
    with open(graph_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                source = parts[0]
                targets = parts[1:]
                link_graph[source] = targets
    return link_graph

def run_hits(link_graph, iterations=50):
    """Run HITS algorithm on citation graph"""
    
    # Get all nodes
    all_nodes = set(link_graph.keys())
    for targets in link_graph.values():
        all_nodes.update(targets)
    
    print(f"Total documents: {len(all_nodes)}")
    print(f"Total citations: {sum(len(v) for v in link_graph.values())}")
    
    # Build reverse graph (incoming citations)
    incoming = defaultdict(list)
    for source, targets in link_graph.items():
        for target in targets:
            incoming[target].append(source)
    
    # Initialize scores
    hubs = {node: 1.0 for node in all_nodes}
    auth = {node: 1.0 for node in all_nodes}
    
    print("\nRunning HITS iterations...")
    for iteration in range(iterations):
        # Update authority scores (cited by good hubs)
        new_auth = {}
        for node in all_nodes:
            new_auth[node] = sum(hubs[in_node] for in_node in incoming[node])
        
        # Update hub scores (links to good authorities)
        new_hubs = {}
        for node in all_nodes:
            new_hubs[node] = sum(auth[out_node] for out_node in link_graph.get(node, []))
        
        # Normalize (Euclidean normalization)
        auth_norm = math.sqrt(sum(v*v for v in new_auth.values()))
        hub_norm = math.sqrt(sum(v*v for v in new_hubs.values()))
        
        for node in all_nodes:
            auth[node] = new_auth[node] / auth_norm if auth_norm > 0 else 0
            hubs[node] = new_hubs[node] / hub_norm if hub_norm > 0 else 0
        
        if (iteration + 1) % 10 == 0:
            print(f"  Iteration {iteration + 1}/{iterations} complete")
    
    return hubs, auth, incoming

def main():
    print("=" * 60)
    print("HITS Algorithm on Cranfield Citation Graph")
    print("=" * 60)
    
    # Load the citation graph
    try:
        link_graph = load_graph("linkgraph.txt")
        print(f"\nLoaded {len(link_graph)} documents with outgoing citations")
    except FileNotFoundError:
        print("\nERROR: linkgraph.txt not found!")
        print("Please run the citation graph builder first.")
        print("You can create it using: python Graph_Cranfield.py")
        return
    
    # Run HITS
    hubs, auth, incoming = run_hits(link_graph, iterations=50)
    
    # Display top authorities (most cited documents)
    print("\n" + "=" * 60)
    print("TOP 20 AUTHORITIES (Most Frequently Cited Documents)")
    print("=" * 60)
    sorted_auth = sorted(auth.items(), key=lambda x: x[1], reverse=True)
    for i, (node, score) in enumerate(sorted_auth[:20]):
        inlink_count = len(incoming.get(node, []))
        print(f"{i+1:3d}. Document {node:4s}: {score:.8f}  (cited by {inlink_count} papers)")
    
    # Display top hubs (documents that cite many others)
    print("\n" + "=" * 60)
    print("TOP 20 HUBS (Documents That Cite the Most Papers)")
    print("=" * 60)
    sorted_hubs = sorted(hubs.items(), key=lambda x: x[1], reverse=True)
    for i, (node, score) in enumerate(sorted_hubs[:20]):
        outlink_count = len(link_graph.get(node, []))
        print(f"{i+1:3d}. Document {node:4s}: {score:.8f}  (cites {outlink_count} papers)")
    
    # Save results
    with open("authority.txt", "w") as f:
        for node, score in sorted_auth:
            inlink_count = len(incoming.get(node, []))
            f.write(f"{node} {score:.8f} {inlink_count}\n")
    
    with open("hub.txt", "w") as f:
        for node, score in sorted_hubs:
            outlink_count = len(link_graph.get(node, []))
            f.write(f"{node} {score:.8f} {outlink_count}\n")
    
    print("\n" + "=" * 60)
    print(f"Results saved to:")
    print(f"  - authority.txt (top cited documents)")
    print(f"  - hub.txt (documents that cite many papers)")
    print("=" * 60)
    
    # Basic statistics
    print("\nStatistics:")
    print(f"  Documents with citations: {len(link_graph)}")
    print(f"  Documents with incoming citations: {len(incoming)}")
    print(f"  Total citation links: {sum(len(v) for v in link_graph.values())}")
    print(f"  Average citations per document: {sum(len(v) for v in link_graph.values()) / len(link_graph):.2f}")

if __name__ == "__main__":
    main()