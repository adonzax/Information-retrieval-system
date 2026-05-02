
from elasticsearch import Elasticsearch
import time
import re

# Elasticsearch connection
ES_HOST = "https://localhost:9200"
ES_USER = "elastic"
ES_PASSWORD = "MFZVm=cRC6mLp3FiuXp0"

es = Elasticsearch(
    ES_HOST,
    basic_auth=(ES_USER, ES_PASSWORD),
    verify_certs=False,
    request_timeout=60
)

INDEX_NAME = "cranfield"  # Your Cranfield index

def extract_citations(biblio_text):
    """
    Extract cited document numbers from bibliography field.
    Cranfield citations typically look like: "1, 2, 3" or "4-7"
    """
    if not biblio_text:
        return []
    
    citations = set()
    
    # Find numbers in the bibliography (potential citations)
    # Pattern matches numbers (1, 2, 10, etc.)
    numbers = re.findall(r'\b\d+\b', biblio_text)
    
    for num in numbers:
        citations.add(num)
    
    # Also handle ranges like "4-7"
    ranges = re.findall(r'(\d+)-(\d+)', biblio_text)
    for start, end in ranges:
        for i in range(int(start), int(end) + 1):
            citations.add(str(i))
    
    return list(citations)

def build_link_graph():
    """Build link graph from Cranfield bibliography citations"""
    
    print("Fetching all documents from Elasticsearch...")
    
    # Get all documents
    response = es.search(
        index=INDEX_NAME,
        body={"query": {"match_all": {}}},
        size=10000,
        _source=["docno", "biblio"]
    )
    
    documents = response['hits']['hits']
    print(f"Found {len(documents)} documents")
    
    # First pass: collect all valid doc IDs
    valid_docnos = set()
    for doc in documents:
        docno = doc['_source'].get('docno', '').strip()
        if docno:
            valid_docnos.add(docno)
    
    print(f"Valid document IDs: {len(valid_docnos)}")
    
    # Build link graph: source -> list of targets (citations)
    link_graph = {}
    
    for doc in documents:
        source = doc['_source'].get('docno', '').strip()
        if not source:
            continue
            
        biblio = doc['_source'].get('biblio', '')
        citations = extract_citations(biblio)
        
        # Only keep citations that actually exist as documents
        valid_citations = [c for c in citations if c in valid_docnos and c != source]
        
        if valid_citations:
            link_graph[source] = valid_citations
            print(f"Document {source} cites: {valid_citations[:5]}..." if len(valid_citations) > 5 else f"Document {source} cites: {valid_citations}")
    
    print(f"\nBuilt graph with {len(link_graph)} nodes having outgoing links")
    
    # Write to file in the expected format
    output_file = "linkgraph.txt"
    with open(output_file, "w") as f:
        for source, targets in link_graph.items():
            line = f"{source} " + " ".join(targets)
            f.write(line + "\n")
    
    print(f"Link graph saved to {output_file}")
    
    # Also count sink nodes (documents with no outgoing citations)
    all_docs_with_citations = set(link_graph.keys())
    sink_nodes = valid_docnos - all_docs_with_citations
    print(f"Sink nodes (no outgoing citations): {len(sink_nodes)}")
    
    return link_graph

if __name__ == "__main__":
    start_time = time.time()
    
    print("Cranfield Citation Graph Builder")
    print("=" * 40)
    
    link_graph = build_link_graph()
    
    # Print statistics
    total_links = sum(len(targets) for targets in link_graph.values())
    print(f"\nStatistics:")
    print(f"  - Documents with citations: {len(link_graph)}")
    print(f"  - Total citation links: {total_links}")
    print(f"  - Average citations per document: {total_links/len(link_graph):.2f}" if link_graph else "  - No links found")
    
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    print(f"\nTime taken: {minutes}:{seconds:02d}")