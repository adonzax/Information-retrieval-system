"""
Cranfield Retrieval Models - Okapi TF, BM25, LM Laplace, LM Jelinek-Mercer, Proximity
"""

import math
import dill
from operator import itemgetter
from collections import defaultdict
import os


class CranfieldRetrievalModels:
    def __init__(self, use_stemming=False):
        self.use_stemming = use_stemming
        self.suffix = "Stemmed" if use_stemming else "Unstemmed"
        
        # Load document info
        with open(f"pickles/docInfo_{self.suffix}.pkl", 'rb') as f:
            self.docInfo = dill.load(f)
        
        self.N = len(self.docInfo)  # Total documents (1400)
        self.avgdl = sum(self.docInfo.values()) / self.N
        self.total_tokens = sum(self.docInfo.values())
        self.V = None  # Vocabulary size - will load from term stats
        
        # Load term list to get vocabulary size
        with open(f"pickles/termStats_{self.suffix}.pkl", 'rb') as f:
            self.term_stats = dill.load(f)
        self.V = len(self.term_stats)
        
        print(f"Loaded {self.suffix} index: N={self.N}, V={self.V}, avgdl={self.avgdl:.2f}")
    
    def load_query_vectors(self, qid):
        """Load pre-processed query vectors"""
        with open(f"pickles/termVector_{self.suffix}_{qid}.pkl", 'rb') as f:
            termVector = dill.load(f)
        with open(f"pickles/termStats_{self.suffix}_{qid}.pkl", 'rb') as f:
            termStats = dill.load(f)
        return termVector, termStats
    
    def restructure_tv(self, termVector):
        """Restructure termVector to doc-centric view"""
        dictDocID = defaultdict(dict)
        for term in termVector:
            for docid in termVector[term]:
                dictDocID[docid][term] = termVector[term][docid]
        return dictDocID
    
    def okapi_tf(self, termVector):
        """
        Okapi TF model (no IDF)
        score = Σ (tf / (tf + 0.5 + 1.5 * (doc_len / avgdl)))
        """
        docScore = []
        dictDocID = self.restructure_tv(termVector)
        
        for docid in dictDocID:
            score = 0
            docLen = self.docInfo.get(docid, 0)
            for term in dictDocID[docid]:
                tfwd = dictDocID[docid][term].getTF()
                score += tfwd / (tfwd + 0.5 + 1.5 * (docLen / self.avgdl))
            docScore.append([docid, score])
        
        docScore.sort(key=itemgetter(1), reverse=True)
        return docScore[:100]
    
    def bm25(self, termVector, k1=1.2, b=0.75):
        """
        Okapi BM25 model
        score = Σ [log((N-df+0.5)/(df+0.5)) × (tf*(k1+1)/(tf + k1*(1-b+b*dl/avgdl)))]
        """
        docScore = []
        dictDocID = self.restructure_tv(termVector)
        
        # Precompute IDF for each term
        idf_cache = {}
        for term in termVector:
            df = len(termVector[term])  # Document frequency
            idf_cache[term] = math.log((self.N - df + 0.5) / (df + 0.5) + 1)
        
        for docid in dictDocID:
            score = 0
            docLen = self.docInfo.get(docid, 0)
            for term in dictDocID[docid]:
                tfwd = dictDocID[docid][term].getTF()
                idf = idf_cache.get(term, 0)
                tf_norm = tfwd * (k1 + 1) / (tfwd + k1 * (1 - b + b * docLen / self.avgdl))
                score += idf * tf_norm
            docScore.append([docid, score])
        
        docScore.sort(key=itemgetter(1), reverse=True)
        return docScore[:100]
    
    def lm_laplace(self, termVector):
        """
        Language Model with Laplace (add-one) smoothing
        P(w|d) = (tf + 1) / (doc_len + V)
        score = Σ log(P(w|d))
        """
        docScore = []
        dictDocID = self.restructure_tv(termVector)
        
        # Get all query terms
        query_terms = set(termVector.keys())
        
        for docid in dictDocID:
            score = 0
            docLen = self.docInfo.get(docid, 0)
            
            for term in query_terms:
                if term in dictDocID[docid]:
                    tfwd = dictDocID[docid][term].getTF()
                    prob = (tfwd + 1) / (docLen + self.V)
                else:
                    prob = 1 / (docLen + self.V)
                score += math.log(prob)
            
            docScore.append([docid, score])
        
        docScore.sort(key=itemgetter(1), reverse=True)
        return docScore[:100]
    
    def lm_jelinek_mercer(self, termVector, lam=0.7):
        """
        Language Model with Jelinek-Mercer smoothing
        P(w|d) = λ * (tf/doc_len) + (1-λ) * (cf/total_tokens)
        score = Σ log(P(w|d))
        """
        docScore = []
        dictDocID = self.restructure_tv(termVector)
        
        # Precompute collection probabilities
        query_terms = set(termVector.keys())
        coll_probs = {}
        for term in query_terms:
            # Get collection frequency from termVector (sum of TFs across docs)
            cf = sum(termVector[term][doc].getTF() for doc in termVector[term])
            coll_probs[term] = cf / self.total_tokens if self.total_tokens > 0 else 0
        
        for docid in dictDocID:
            score = 0
            docLen = self.docInfo.get(docid, 0)
            
            for term in query_terms:
                if term in dictDocID[docid]:
                    tfwd = dictDocID[docid][term].getTF()
                    doc_prob = tfwd / docLen
                else:
                    doc_prob = 0
                
                prob = lam * doc_prob + (1 - lam) * coll_probs.get(term, 0)
                if prob > 0:
                    score += math.log(prob)
                else:
                    score += -100  # Large negative for zero probability
            
            docScore.append([docid, score])
        
        docScore.sort(key=itemgetter(1), reverse=True)
        return docScore[:100]
    
    def proximity_search(self, termVector, c=1500):
        """
        Proximity search - scores based on how close query terms appear
        score = (c - min_span) * num_terms / (doc_len + V)
        """
        docScore = []
        
        for docid, term_data in termVector.items():
            # Get positions for all query terms in this document
            positions = {}
            for term, tv in term_data.items():
                positions[term] = tv.getPos()
            
            if len(positions) < 2:
                # Only one term - use TF-IDF style score
                tf_sum = sum(tv.getTF() for tv in term_data.values())
                docLen = self.docInfo.get(docid, 0)
                score = tf_sum / (docLen + self.V)
                docScore.append([docid, score])
                continue
            
            # Find minimum window containing all query terms
            # Convert to list of (term, position)
            all_positions = []
            for term, pos_list in positions.items():
                for pos in pos_list:
                    all_positions.append((term, pos))
            
            all_positions.sort(key=lambda x: x[1])
            
            # Slide window to find minimal span covering all terms
            term_counts = defaultdict(int)
            unique_terms = len(positions)
            min_span = float('inf')
            left = 0
            
            for right in range(len(all_positions)):
                term_counts[all_positions[right][0]] += 1
                
                while len(term_counts) == unique_terms:
                    span = all_positions[right][1] - all_positions[left][1]
                    if span < min_span:
                        min_span = span
                    
                    # Move left pointer
                    term_counts[all_positions[left][0]] -= 1
                    if term_counts[all_positions[left][0]] == 0:
                        del term_counts[all_positions[left][0]]
                    left += 1
            
            # Calculate score
            num_terms = unique_terms
            docLen = self.docInfo.get(docid, 0)
            score = (c - min_span) * num_terms / (docLen + self.V)
            docScore.append([docid, score])
        
        docScore.sort(key=itemgetter(1), reverse=True)
        return docScore[:100]
    
    def run_all_models(self, query_range=range(1, 226)):
        """Run all models for all queries"""
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)
        
        models = {
            'OkapiTF': self.okapi_tf,
            'BM25': self.bm25,
            'LM_Laplace': self.lm_laplace,
            'LM_JelinekMercer': self.lm_jelinek_mercer,
            'Proximity': self.proximity_search
        }
        
        for model_name, model_func in models.items():
            output_file = f"{results_dir}/{self.suffix}_{model_name}_Results.txt"
            print(f"\nRunning {model_name} on {self.suffix} index...")
            
            with open(output_file, 'w') as f:
                for qid in query_range:
                    try:
                        termVector, _ = self.load_query_vectors(qid)
                        results = model_func(termVector)
                        
                        for rank, (docid, score) in enumerate(results, 1):
                            f.write(f"{qid} Q0 {docid} {rank} {score:.6f} Exp\n")
                        
                        if qid % 50 == 0:
                            print(f"  Processed {qid} queries...")
                    except FileNotFoundError:
                        print(f"  Warning: Query {qid} not found, skipping...")
            
            print(f"  Saved to {output_file}")


def main():
    print("=" * 50)
    print("Cranfield Retrieval Models")
    print("=" * 50)
    
    # Run on unstemmed index
    print("\n" + "=" * 50)
    print("Running on UNSTEMMED index")
    print("=" * 50)
    unstemmed_models = CranfieldRetrievalModels(use_stemming=False)
    unstemmed_models.run_all_models()
    
    # Run on stemmed index
    print("\n" + "=" * 50)
    print("Running on STEMMED index")
    print("=" * 50)
    stemmed_models = CranfieldRetrievalModels(use_stemming=True)
    stemmed_models.run_all_models()
    
    print("\n" + "=" * 50)
    print("All models completed!")
    print("=" * 50)


if __name__ == "__main__":
    main()