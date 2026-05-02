from collections import OrderedDict
import math
import sys

relevanceJudgements = {}

def retrieveQueryResults(rankList):
    queryResults = OrderedDict()
    with open(rankList, 'r') as f:
        for queryResult in f:
            items = queryResult.split()
            if len(items) < 3:
                continue
            queryID = items[0]
            documentID = items[2]
            if queryID in queryResults:
                queryResults[queryID].append(documentID)
            else:
                queryResults[queryID] = [documentID]
    return queryResults

def getRevelanceJudgements(qrel):
    with open(qrel, 'r') as f:
        for judgement in f:
            cols = judgement.split()
            if len(cols) < 3:
                continue
            queryID = cols[0]
            documentID = cols[1]
            relevance = cols[2].strip()
            if relevance not in ['0', '-1']:
                if queryID in relevanceJudgements:
                    if documentID not in relevanceJudgements[queryID]:
                        relevanceJudgements[queryID].append(documentID)
                else:
                    relevanceJudgements[queryID] = [documentID]

def designateVals(lst, val, rank):
    if rank in lst:
        lst[rank].append(val)
    else:
        lst[rank] = [val]
    return lst

def printMeanVals(lst, desc, kVals=[], qid=''):
    if not kVals:
        if len(lst) > 0:
            print(desc + ': ' + str("{:.4f}".format(math.fsum(lst) / len(lst))))
    else:
        for k in kVals:
            if k in lst and len(lst[k]) > 0:
                if qid != '':
                    print(desc + str(k) + ' for ' + qid + ': ' + str("{:.4f}".format(math.fsum(lst[k]) / len(lst[k]))))
                else:
                    print(desc + str(k) + ': ' + str("{:.4f}".format(math.fsum(lst[k]) / len(lst[k]))))

def calculateMetrics(queryResults, option):
    kVals = [5, 10, 20, 50, 100]
    qid = 0
    AP, RP, NDCG = [], [], []
    P, R, F1 = {}, {}, {}
    
    for queryID in queryResults:
        qid += 1
        relevanceScore = []
        psum, rank, relevantNumber, rp = 0, 0, 0, 0
        results = queryResults[queryID]
        
        if queryID in relevanceJudgements:
            relevantDocuments = relevanceJudgements[queryID]
        else:
            continue
            
        for document in results:
            rank += 1
            isRelevant = 0
            if document in relevantDocuments:
                relevantNumber += 1
                isRelevant = 1
            if rank <= len(relevantDocuments):
                rp = relevantNumber
            precision = relevantNumber / (rank * 1.0)
            if isRelevant == 1:
                psum += precision
            recall = 0 if len(relevantDocuments) == 0 else relevantNumber / (len(relevantDocuments) * 1.0)
            
            if rank in kVals:
                P = designateVals(P, precision, rank)
                if relevantNumber > 0:
                    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                else:
                    f1 = 0
                F1 = designateVals(F1, f1, rank)
                R = designateVals(R, recall, rank)

            relevanceScore.append(isRelevant)
        
        # Calculate nDCG
        j = 0
        dc_value = 0.0
        for score in relevanceScore:
            j += 1
            dc_value += (score) / math.log((1.0 + j))
        j = 0
        idc_value = 0.0
        relevanceScore_sorted = sorted(relevanceScore, reverse=True)
        for score in relevanceScore_sorted:
            j += 1
            idc_value += (score) / math.log((1.0 + j))
        
        if len(relevantDocuments) > 0:
            rPrecision = rp / len(relevantDocuments)
        else:
            rPrecision = 0.0
        RP.append(rPrecision)
        
        if idc_value == 0.0:
            ndcg = 0.0
        else:
            ndcg = dc_value / idc_value
        NDCG.append(ndcg)

        avgPrecision = 0.0
        if relevantNumber != 0:
            avgPrecision = psum / (len(relevantDocuments) * 1.0)
        AP.append(avgPrecision)

    printMeanVals(AP, 'Average Precision')
    printMeanVals(RP, 'R-precision')
    printMeanVals(NDCG, 'nDCG')
    print('\nPrecision@ Values')
    printMeanVals(P, 'Mean Precision@', kVals)
    print('\nRecall@ Values')
    printMeanVals(R, 'Mean Recall@', kVals)
    print('\nF1@ Values')
    printMeanVals(F1, 'Mean F1@', kVals)

def main():
    if len(sys.argv) < 3:
        print("Usage: python Trec_Eval.py <qrels_file> <ranklist_file>")
        print("Example: python Trec_Eval.py cranqrel OkapiBM25_Results_File.txt")
        return
    
    qrels_file = sys.argv[1]
    ranklist_file = sys.argv[2]
    
    print(f"Evaluating: {ranklist_file}")
    print("-" * 50)
    
    queryResults = retrieveQueryResults(ranklist_file)
    getRevelanceJudgements(qrels_file)
    calculateMetrics(queryResults, 2)

if __name__ == "__main__":
    main()