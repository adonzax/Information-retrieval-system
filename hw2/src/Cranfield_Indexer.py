
import re
import dill
import os
import time
from collections import defaultdict, OrderedDict
from stemming.porter2 import stem

# ==================== Term Vector Class ====================
class TermVector:
    def __init__(self, tf, pos):
        self.tf = tf
        self.pos = pos

    def getTF(self):
        return self.tf

    def getPos(self):
        return self.pos


# ==================== Cranfield Parser ====================
def parse_cranfield_documents(filepath):
    """
    Parse Cranfield .I/.T/.A/.B/.W format
    
    Format:
    .I
    1
    .T
    title
    .A
    author
    .B
    bibliography
    .W
    abstract text...
    """
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line == '.I':
            i += 1
            doc_id = int(lines[i].strip())
            text = ""
            
            # Skip .T, .A, .B to find .W
            while i < len(lines):
                i += 1
                if i >= len(lines):
                    break
                current = lines[i].strip()
                if current == '.W':
                    i += 1
                    # Read abstract until next field
                    while i < len(lines):
                        next_line = lines[i].strip()
                        if next_line in ['.I', '.T', '.A', '.B']:
                            break
                        text += lines[i] + " "
                        i += 1
                    break
            
            yield doc_id, text.strip()
        else:
            i += 1


# ==================== Tokenizer ====================
def tokenizer(text, remove_stopwords=True, do_stemming=False):
    """
    Tokenize text for Cranfield
    
    Args:
        text: Input text
        remove_stopwords: Remove stopwords
        do_stemming: Apply Porter2 stemming
    
    Returns:
        list of [token, position] pairs
    """
    global stopWords
    
    posToken = []
    position = 0
    
    # Split on non-alphanumeric characters (keep periods for numbers)
    tokens = re.split(r"[^\w\.]+", text)
    
    for token in tokens:
        if not token:
            continue
        
        # Clean token
        token = token.lower()
        
        # Remove trailing period (but keep decimal points)
        if token.endswith('.') and not token[:-1].isdigit():
            token = token[:-1]
        
        # Skip single characters
        if len(token) < 2:
            continue
        
        # Remove stopwords
        if remove_stopwords and token in stopWords:
            continue
        
        # Apply stemming
        if do_stemming:
            token = stem(token)
        
        position += 1
        posToken.append([token, position])
    
    return posToken


# ==================== Inverted Index Builder ====================
class CranfieldIndexer:
    def __init__(self, use_stemming=False):
        self.use_stemming = use_stemming
        self.suffix = "Stemmed" if use_stemming else "Unstemmed"
        self.term_dict = defaultdict(lambda: defaultdict(TermVector))
        self.docInfo = {}           # doc_id -> document length
        self.total_tokens = 0
        self.num_docs = 0
        self.term_stats = {}        # term -> [df, ttf]
        
    def build(self, corpus_path):
        """Build inverted index from Cranfield corpus"""
        print(f"Building Cranfield index (stemming={self.use_stemming})...")
        start_time = time.time()
        
        for doc_id, text in parse_cranfield_documents(corpus_path):
            # Tokenize
            tokens = tokenizer(text, remove_stopwords=True, do_stemming=self.use_stemming)
            
            # Store document length
            self.docInfo[doc_id] = len(tokens)
            self.total_tokens += len(tokens)
            self.num_docs += 1
            
            # Count term frequencies in this document
            tf_dict = defaultdict(int)
            pos_dict = defaultdict(list)
            
            for pos, token in enumerate(tokens, 1):
                token_str = token[0] if isinstance(token, list) else token
                tf_dict[token_str] += 1
                pos_dict[token_str].append(pos)
            
            # Update index
            for term, tf in tf_dict.items():
                self.term_dict[term][doc_id] = TermVector(tf, pos_dict[term])
            
            # Progress update
            if self.num_docs % 100 == 0:
                print(f"  Processed {self.num_docs} documents...")
        
        # Calculate term statistics
        print("Calculating term statistics...")
        for term, docs in self.term_dict.items():
            df = len(docs)
            ttf = sum(docs[doc].getTF() for doc in docs)
            self.term_stats[term] = [df, ttf]
        
        elapsed = time.time() - start_time
        print(f"\nIndex built successfully!")
        print(f"  Documents: {self.num_docs}")
        print(f"  Vocabulary size: {len(self.term_dict)}")
        print(f"  Total tokens: {self.total_tokens}")
        print(f"  Average doc length: {self.total_tokens/self.num_docs:.2f}")
        print(f"  Time: {elapsed:.2f} seconds")
        
        return self
    
    def save(self, output_dir="pickles"):
        """Save index to pickle files"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save term dictionary
        with open(f"{output_dir}/termDict_{self.suffix}.pkl", 'wb') as f:
            dill.dump(dict(self.term_dict), f)
        
        # Save document info
        with open(f"{output_dir}/docInfo_{self.suffix}.pkl", 'wb') as f:
            dill.dump(self.docInfo, f)
        
        # Save term statistics
        with open(f"{output_dir}/termStats_{self.suffix}.pkl", 'wb') as f:
            dill.dump(self.term_stats, f)
        
        # Save catalog (term list)
        with open(f"{output_dir}/catalog_{self.suffix}.txt", 'w') as f:
            for term_id, term in enumerate(sorted(self.term_dict.keys()), 1):
                df, ttf = self.term_stats[term]
                f.write(f"{term_id},{term},{df},{ttf}\n")
        
        print(f"Index saved to {output_dir}/")
    
    def load(self, output_dir="pickles"):
        """Load index from pickle files"""
        with open(f"{output_dir}/termDict_{self.suffix}.pkl", 'rb') as f:
            self.term_dict = defaultdict(lambda: defaultdict(TermVector), dill.load(f))
        
        with open(f"{output_dir}/docInfo_{self.suffix}.pkl", 'rb') as f:
            self.docInfo = dill.load(f)
        
        with open(f"{output_dir}/termStats_{self.suffix}.pkl", 'rb') as f:
            self.term_stats = dill.load(f)
        
        self.num_docs = len(self.docInfo)
        self.total_tokens = sum(self.docInfo.values())
        
        print(f"Index loaded: {self.num_docs} docs, {len(self.term_dict)} terms")
        return self
    
    def get_posting_list(self, term):
        """Get posting list for a term"""
        return self.term_dict.get(term, {})
    
    def get_df(self, term):
        """Get document frequency"""
        stats = self.term_stats.get(term)
        return stats[0] if stats else 0
    
    def get_ttf(self, term):
        """Get total term frequency (collection frequency)"""
        stats = self.term_stats.get(term)
        return stats[1] if stats else 0
    
    def get_avg_doc_len(self):
        return self.total_tokens / self.num_docs if self.num_docs > 0 else 0


# ==================== Load Stopwords ====================
def load_stopwords(filepath="stoplist.txt"):
    """Load stopwords from file"""
    if not os.path.exists(filepath):
        # Create default stopwords if file doesn't exist
        default_stopwords = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'were', 'will', 'with', 'the', 'this', 'that', 'these',
            'those', 'am', 'do', 'does', 'did', 'doing', 'have', 'having',
            'not', 'no', 'but', 'or', 'so', 'for', 'yet', 'at', 'by', 'up',
            'down', 'off', 'over', 'under', 'again', 'further', 'then', 'once'
        }
        return default_stopwords
    
    with open(filepath, 'r') as f:
        return set(line.strip().lower() for line in f if line.strip())


# ==================== Main ====================
def main():
    global stopWords
    stopWords = load_stopwords()
    
    # Build unstemmed index
    print("=" * 50)
    print("Building UNSTEMMED index (stopwords removed)")
    print("=" * 50)
    unstemmed_index = CranfieldIndexer(use_stemming=False)
    unstemmed_index.build("data/cran.all.1400")
    unstemmed_index.save("pickles")
    
    # Build stemmed index
    print("\n" + "=" * 50)
    print("Building STEMMED index (stopwords + stemming)")
    print("=" * 50)
    stemmed_index = CranfieldIndexer(use_stemming=True)
    stemmed_index.build("data/cran.all.1400")
    stemmed_index.save("pickles")
    
    print("\n" + "=" * 50)
    print("Indexing complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()