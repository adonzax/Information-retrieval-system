from collections import OrderedDict
import math

relevanceJudgements = {}

def retrieveQueryResults(rankList):
    queryResults = OrderedDict()
    with open(rankList, 'r') as f:
        for queryResult in f:
            items = queryResult.split()
            if len(items) < 3:
                continue
            queryID = items[0]
            documentID = items[2]  # TREC format: qid Q0 docid rank score run
            if queryID in queryResults:
                queryResults[queryID].append(documentID)
            else:
                queryResults[queryID] = [documentID]
    return queryResults

def getRevelanceJudgements(qrel):
    """For Cranfield format: qid docid relevance (3 columns)"""
    with open(qrel, 'r') as f:
        for judgement in f:
            cols = judgement.split()
            if len(cols) < 3:
                continue
            queryID = cols[0]
            documentID = cols[1]      # Cranfield: docid is column 2
            relevance = cols[2].strip()  # Cranfield: relevance is column 3
            
            # Treat any positive relevance as relevant (1,2,3,4)
            if relevance != '0' and relevance != '-1':
                if queryID in relevanceJudgements:
                    if documentID not in relevanceJudgements[queryID]:
                        relevanceJudgements[queryID].append(documentID)
                else:
                    relevanceJudgements[queryID] = [documentID]

def getScoreForID(queryID, documents):
    relevanceScore = []
    relevantDocuments = []
    if queryID in relevanceJudgements:
        relevantDocuments = relevanceJudgements[queryID]
    for document in documents:
        if document in relevantDocuments:
            relevanceScore.append(1)
        else:
            relevanceScore.append(0)
    return relevanceScore

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
            print(desc + ': 0.0000')
    else:
        for k in kVals:
            if k in lst and len(lst[k]) > 0:
                if qid != '':
                    print(desc + str(k) + ' for ' + qid + ': ' + str("{:.4f}".format(math.fsum(lst[k]) / len(lst[k]))))
                else:
                    print(desc + str(k) + ': ' + str("{:.4f}".format(math.fsum(lst[k]) / len(lst[k]))))
            else:
                if qid != '':
                    print(desc + str(k) + ' for ' + qid + ': 0.0000')
                else:
                    print(desc + str(k) + ': 0.0000')

def calculateMetrics(queryResults, option):
    kVals = [5, 10, 20, 50, 100]
    qid = 0
    AP, RP, NDCG = [], [], []
    P, R, F1 = {}, {}, {}
    f = open("details.txt", 'w')
    
    for queryID in queryResults:
        qid += 1
        relevanceScore = []
        PTemp, RTemp, F1Temp = {}, {}, {}
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
                PTemp = designateVals(PTemp, precision, rank)
                if (relevantNumber > 0):
                    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                else:
                    f1 = 0
                F1 = designateVals(F1, f1, rank)
                F1Temp = designateVals(F1Temp, f1, rank)
                R = designateVals(R, recall, rank)
                RTemp = designateVals(RTemp, recall, rank)

            relevanceScore.append(isRelevant)
            f.write(queryID + ' ' + document + ' ' + str(rank) + ' ' + str(isRelevant) + ' ' + 
                    str("{:.4f}".format(precision)) + ' ' + str("{:.4f}".format(recall)) + '\n')
        
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
        
        if option == 1:
            print('Average Precision for ' + queryID + ': ' + str("{:.4f}".format(avgPrecision)))
            print('R-precision for ' + queryID + ': ' + str("{:.4f}".format(rPrecision)))
            print('nDCG for ' + queryID + ': ' + str("{:.4f}".format(ndcg)) + '\n')
            print('Precision@ Values')
            printMeanVals(PTemp, 'Mean Precision@', kVals, queryID)
            print('\nRecall@ Values')
            printMeanVals(RTemp, 'Mean Recall@', kVals, queryID)
            print('\nF1@ Values')
            printMeanVals(F1Temp, 'Mean F1@', kVals, queryID)
            print('\n')

    printMeanVals(AP, 'Average Precision')
    printMeanVals(RP, 'R-precision')
    printMeanVals(NDCG, 'nDCG')
    print('\nPrecision@ Values')
    printMeanVals(P, 'Mean Precision@', kVals)
    print('\nRecall@ Values')
    printMeanVals(R, 'Mean Recall@', kVals)
    print('\nF1@ Values')
    printMeanVals(F1, 'Mean F1@', kVals)
    f.close()

def main():
    cmd = input('Enter command: ')
    cmd_params = cmd.split(' ')
    
    if len(cmd_params) == 3:
        # Format: trec_eval qrels.txt rankList.txt
        queryResults = retrieveQueryResults(cmd_params[2])
        getRevelanceJudgements(cmd_params[1])
        calculateMetrics(queryResults, 2)
    elif len(cmd_params) == 4 and cmd_params[1] == '-q':
        # Format: trec_eval -q qrels.txt rankList.txt
        queryResults = retrieveQueryResults(cmd_params[3])
        getRevelanceJudgements(cmd_params[2])
        calculateMetrics(queryResults, 1)
    else:
        print("Usage: trec_eval [-q] qrels.txt rankList.txt")
        print("Example: trec_eval cranqrel OkapiBM25_Results_File.txt")
        print("Example: trec_eval -q cranqrel OkapiBM25_Results_File.txt")

if __name__ == "__main__":
    main()