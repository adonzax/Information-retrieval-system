from collections import OrderedDict
import re
import math
import string
import dill
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
import csv

relevanceJudgements = {}
featureMatrix = OrderedDict()
qrelDocIDs = []

# Connect to Elasticsearch (your Cranfield index)
es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", "MFZVm=cRC6mLp3FiuXp0"),
    verify_certs=False,
    request_timeout=60
)

# Use your Cranfield index
INDEX_NAME = "cranfield"
FIELD_NAME = "body_text"  # Cranfield uses body_text, not "text"

# Get vocabulary size from Cranfield index
s = Search(using=es, index=INDEX_NAME)
s = s.source([])
s.aggs.bucket("vocabSize", "cardinality", field=FIELD_NAME)
res = s.execute()
V = res.aggregations.vocabSize.value

print(f"Vocabulary size (V): {V}")

# Load term frequency data (from your HW2 work)
# You'll need to create totalTF.p from Cranfield data first
try:
    f = open('totalTF.p', 'rb')
    cTF = dill.load(f)
    f.close()
except FileNotFoundError:
    print("totalTF.p not found. Creating from Cranfield index...")
    cTF = []  # You'd need to build this from your Cranfield index
    # See note below about creating totalTF.p

relevance = {}

def getRevelanceJudgements(qrel):
    """For Cranfield 3-column format"""
    with open(qrel, 'r') as f:
        for judgement in f:
            cols = judgement.split()
            if len(cols) < 3:
                continue
            queryID = cols[0]
            documentID = cols[1]  # Cranfield: docid is column 2
            relevance_val = int(cols[2])  # Cranfield: relevance is column 3
            
            if queryID in relevance:
                relevance[queryID][documentID] = relevance_val
            else:
                relevance[queryID] = {}
                relevance[queryID][documentID] = relevance_val
            
            if queryID in relevanceJudgements:
                relevanceJudgements[queryID].append((documentID, 'na'))
            else:
                relevanceJudgements[queryID] = [(documentID, 'na')]

def getDocScoreFromRM(rmFile, ds):
    """Read retrieval model results from TREC format file"""
    with open(rmFile, 'r') as f:
        for res in f:
            cols = res.split()
            if len(cols) < 6:
                continue
            queryID = cols[0]
            documentID = cols[2]
            score = cols[4].strip()
            if queryID in ds:
                ds[queryID].append((documentID, score))
            else:
                ds[queryID] = [(documentID, score)]

def queryProcessor(query, stoplist_file='stoplist.txt'):
    """Remove stopwords from query"""
    try:
        with open(stoplist_file, 'r') as sfile:
            stopWords = [w.strip() for w in sfile.readlines() if w.strip()]
    except FileNotFoundError:
        # Default stopwords if file not found
        stopWords = ['a', 'an', 'and', 'the', 'of', 'to', 'in', 'for', 'on', 'with']
    
    keywords = []
    for word in query.split():
        if word.lower() not in stopWords:
            keywords.append(word)
    
    # Remove punctuation
    table = str.maketrans('', '', string.punctuation)
    cleaned = " ".join(keywords).translate(table)
    return cleaned.strip()

def queryMaker(qID):
    """Get query text from Cranfield qry file"""
    # You'll need to have cran.qry file accessible
    # For now, return a placeholder or read from file
    queries = {
        '1': "Causes of world war 2",
        '2': "Battles won by USA in World War 2", 
        '3': "Battle of Stalingrad"
    }
    return [queries.get(str(qID), "")]

def UnigramLM_Laplace(qNo, docID, query):
    """Calculate Laplace smoothed LM score"""
    keywords = queryProcessor(query).lower()
    docScore = 0.0
    
    # Get document length from Elasticsearch
    try:
        tv = es.termvectors(index=INDEX_NAME, id=docID, fields=FIELD_NAME)
        docLen = sum(info['term_freq'] for info in tv['term_vectors'][FIELD_NAME]['terms'].values())
    except:
        docLen = 100  # default
    
    for key in keywords.split():
        # Get term frequency in document
        tf = 0
        try:
            tv = es.termvectors(index=INDEX_NAME, id=docID, fields=FIELD_NAME, term_statistics=True)
            if key in tv['term_vectors'][FIELD_NAME]['terms']:
                tf = tv['term_vectors'][FIELD_NAME]['terms'][key]['term_freq']
        except:
            pass
        
        score = (tf + 1) / (docLen + V)
        docScore += math.log(score)
    
    return docScore

def UnigramLM_JelinekMercer(qNo, query):
    """Calculate Jelinek-Mercer smoothed LM score (simplified)"""
    keywords = queryProcessor(query).lower()
    l = 0.8
    docScore = 0.0
    
    for key in keywords.split():
        # Get collection frequency from your cTF data
        cf = 1  # default - should come from cTF
        pML = cf / V
        score = (float(1 - l) * pML)
        docScore += math.log(score)
    
    return docScore

def get1000Scores(ds, opt=0):
    """Get top 1000 scores per query"""
    ds1000 = {}
    
    for qID in relevanceJudgements:
        if qID in ds:
            ds1000[qID] = []
            if opt != 0:
                docIDLst[qID] = []
            for docScorePair in relevanceJudgements[qID]:
                if opt != 0:
                    docIDLst[qID].append(docScorePair[0])
                    pair = [item for item in ds[qID] if item[0] == docScorePair[0]]
                    if pair:
                        score = pair[0][1]
                    else:
                        score = ''
                    ds1000[qID].append((docScorePair[0], score))
                else:
                    if docScorePair[0] in docIDLst[qID]:
                        pair = [item for item in ds[qID] if item[0] == docScorePair[0]]
                        if pair:
                            score = pair[0][1]
                        else:
                            score = ''
                        ds1000[qID].append((docScorePair[0], score))
    
    return ds1000

def generateScores(ds1000, model):
    """Generate scores for missing documents"""
    ds1000Temp = {}
    for qid in ds1000:
        ds1000Temp[qid] = []
        for docScorePair in ds1000[qid]:
            pair = [item for item in ds1000[qid] if item[0] == docScorePair[0]][0][1]
            if pair == '' or pair == 0:
                query = queryMaker(qid)
                if model in ['BM25', 'TF-IDF', 'Okapi TF']:
                    pair = 0.001  # small default
                elif model == 'Jelinek-Mercer':
                    pair = UnigramLM_JelinekMercer(qid, query[0])
                else:
                    pair = UnigramLM_Laplace(qid, docScorePair[0], query[0])
            ds1000Temp[qid].append((docScorePair[0], pair))
    return ds1000Temp

def createFeatureMatrix(ds1000, model, opt=0):
    """Create feature matrix from scores"""
    for qID in ds1000:
        for docScorePair in ds1000[qID]:
            if docScorePair[0] in relevance.get(qID, {}):
                label = relevance[qID][docScorePair[0]]
            else:
                label = 0
            
            # Only include documents with label > 0 (relevant) for training
            if opt != 0 or label > 0:
                identifier = str(qID) + '-' + docScorePair[0]
                if opt != 0:
                    featureMatrix[identifier] = OrderedDict()
                    featureMatrix[identifier][model] = [float(docScorePair[1]) if docScorePair[1] else 0, label]
                else:
                    if identifier in featureMatrix:
                        featureMatrix[identifier][model] = [float(docScorePair[1]) if docScorePair[1] else 0, label]
                    else:
                        featureMatrix[identifier] = OrderedDict()
                        featureMatrix[identifier][model] = [float(docScorePair[1]) if docScorePair[1] else 0, label]

def staticFeatureMatrixCSV():
    """Write feature matrix to CSV"""
    with open('staticFeatureMatrix.csv', 'w', newline='') as csvfile:
        filewriter = csv.writer(csvfile, delimiter=',')
        filewriter.writerow(['QID-DocID', 'TF-IDF', 'Okapi TF', 'BM25', 'Laplace', 'Jelinek-Mercer', 'Label'])
        
        for identifier in featureMatrix:
            tfidf = featureMatrix[identifier].get('TF-IDF', [0, 0])[0]
            okapi = featureMatrix[identifier].get('Okapi TF', [0, 0])[0]
            bm25 = featureMatrix[identifier].get('BM25', [0, 0])[0]
            laplace = featureMatrix[identifier].get('Laplace', [0, 0])[0]
            jm = featureMatrix[identifier].get('Jelinek-Mercer', [0, 0])[0]
            label = featureMatrix[identifier].get('TF-IDF', [0, 0])[1]
            
            filewriter.writerow([identifier, tfidf, okapi, bm25, laplace, jm, label])

# Global variable for document ID list
docIDLst = {}

def main():
    print("Step 1: Loading relevance judgments (Cranfield format)...")
    getRevelanceJudgements("cranqrel")  # Your Cranfield qrels file
    
    print("Step 2: Loading retrieval model results...")
    # Initialize score dictionaries
    bm25Scores = {}
    jmScores = {}
    lScores = {}
    oTFScores = {}
    tfIDFScores = {}
    
        # Load your result files (adjust paths as needed)
    getDocScoreFromRM("hw2_result/OkapiBM25_Results_File.txt", bm25Scores)
    getDocScoreFromRM("hw2_result/UnigramLMJM_Results_File.txt", jmScores)
    getDocScoreFromRM("hw2_result/UnigramLMLaplace_Results_File.txt", lScores)
    getDocScoreFromRM("hw2_result/OkapiTF_Results_File.txt", oTFScores)
    getDocScoreFromRM("hw2_result/TF-IDF_Results_File.txt", tfIDFScores)
    
    print("Step 3: Creating score matrices...")
    bm25Scores1000 = get1000Scores(bm25Scores, 1)
    jmScores1000 = get1000Scores(jmScores)
    lScores1000 = get1000Scores(lScores)
    oTFScores1000 = get1000Scores(oTFScores)
    tfIDFScores1000 = get1000Scores(tfIDFScores)
    
    print("Step 4: Generating scores...")
    bm25Scores1000Scored = generateScores(bm25Scores1000, 'BM25')
    jmScores1000Scored = generateScores(jmScores1000, 'Jelinek-Mercer')
    lScores1000Scored = generateScores(lScores1000, 'Laplace')
    oTFScores1000Scored = generateScores(oTFScores1000, 'Okapi TF')
    tfIDFScores1000Scored = generateScores(tfIDFScores1000, 'TF-IDF')
    
    print("Step 5: Creating feature matrix...")
    createFeatureMatrix(tfIDFScores1000Scored, 'TF-IDF', 1)
    createFeatureMatrix(oTFScores1000Scored, 'Okapi TF')
    createFeatureMatrix(bm25Scores1000Scored, 'BM25')
    createFeatureMatrix(lScores1000Scored, 'Laplace')
    createFeatureMatrix(jmScores1000Scored, 'Jelinek-Mercer')
    
    print("Step 6: Writing CSV...")
    staticFeatureMatrixCSV()
    
    print(f"Feature matrix created with {len(featureMatrix)} query-document pairs")
    print("Output saved to staticFeatureMatrix.csv")

if __name__ == "__main__":
    main()