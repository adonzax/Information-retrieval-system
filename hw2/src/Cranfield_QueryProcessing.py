"""
Cranfield Query Processor - Converts queries to term vectors
"""

import re
import dill
from collections import OrderedDict
from stemming.porter2 import stem

# Import from indexer
from Cranfield_Indexer import tokenizer, load_stopwords


def parse_cranfield_queries(filepath):
    """
    Parse Cranfield query file (.I/.W format)
    
    Returns:
        dict: {query_id: query_text}
    """
    queries = {}
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line == '.I':
            i += 1
            qid = int(lines[i].strip())
            text = ""
            
            # Find .W field
            while i < len(lines):
                i += 1
                if i >= len(lines):
                    break
                if lines[i].strip() == '.W':
                    i += 1
                    while i < len(lines):
                        if lines[i].strip() == '.I':
                            break
                        text += lines[i] + " "
                        i += 1
                    break
            
            queries[qid] = text.strip()
        else:
            i += 1
    
    return queries


class CranfieldQueryProcessor:
    def __init__(self, use_stemming=False):
        self.use_stemming = use_stemming
        self.suffix = "Stemmed" if use_stemming else "Unstemmed"
        
        # Load stopwords
        self.stopWords = load_stopwords()
        
        # Load index
        self.load_index()
    
    def load_index(self):
        """Load pre-built index"""
        import dill
        
        # Load term dictionary
        with open(f"pickles/termDict_{self.suffix}.pkl", 'rb') as f:
            self.term_dict = dill.load(f)
        
        # Load term statistics
        with open(f"pickles/termStats_{self.suffix}.pkl", 'rb') as f:
            self.term_stats = dill.load(f)
        
        # Load document info
        with open(f"pickles/docInfo_{self.suffix}.pkl", 'rb') as f:
            self.docInfo = dill.load(f)
        
        print(f"Loaded {self.suffix} index: {len(self.term_dict)} terms, {len(self.docInfo)} docs")
    
    def process_query(self, query_text):
        """
        Convert query to term vector
        
        Returns:
            termVector: dict of {term: {doc_id: TermVector}}
            termStats: dict of {term: [df, ttf]}
        """
        # Tokenize query (same as documents)
        tokens = tokenizer(query_text, remove_stopwords=True, do_stemming=self.use_stemming)
        
        # Get unique terms
        query_terms = list(set(t[0] for t in tokens))
        
        termVector = OrderedDict()
        termStats = OrderedDict()
        
        for term in query_terms:
            if term in self.term_dict:
                termVector[term] = self.term_dict[term]
                termStats[term] = self.term_stats[term]
        
        return termVector, termStats
    
    def process_all_queries(self, query_file="data/cran.qry"):
        """Process all queries and save term vectors"""
        import dill
        
        queries = parse_cranfield_queries(query_file)
        print(f"Processing {len(queries)} queries...")
        
        for qid, query_text in queries.items():
            termVector, termStats = self.process_query(query_text)
            
            # Save term vector
            with open(f"pickles/termVector_{self.suffix}_{qid}.pkl", 'wb') as f:
                dill.dump(termVector, f)
            
            # Save term stats
            with open(f"pickles/termStats_{self.suffix}_{qid}.pkl", 'wb') as f:
                dill.dump(termStats, f)
            
            if qid % 50 == 0:
                print(f"  Processed {qid} queries...")
        
        print(f"All queries processed!")


def main():
    print("=" * 50)
    print("Processing Queries for Cranfield")
    print("=" * 50)
    
    # Process for unstemmed index
    print("\nProcessing for UNSTEMMED index...")
    processor_unstemmed = CranfieldQueryProcessor(use_stemming=False)
    processor_unstemmed.process_all_queries()
    
    # Process for stemmed index
    print("\nProcessing for STEMMED index...")
    processor_stemmed = CranfieldQueryProcessor(use_stemming=True)
    processor_stemmed.process_all_queries()
    
    print("\nDone!")


if __name__ == "__main__":
    main()