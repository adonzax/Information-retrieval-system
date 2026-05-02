import pandas as pd
import numpy as np
from sklearn import model_selection
from sklearn import linear_model
from operator import itemgetter

def createDict(qdIDTest, predictions):
    testDict = {}
    for i, prediction in enumerate(predictions):
        # Convert to regular Python string - THIS IS THE KEY FIX
        qdIDVal = str(qdIDTest[i])
        
        # Split into QID and DocID
        if '-' in qdIDVal:
            parts = qdIDVal.split('-', 1)
            qID = parts[0]
            docID = parts[1]
        else:
            continue
            
        if qID in testDict:
            testDict[qID].append((docID, prediction))
        else:
            testDict[qID] = [(docID, prediction)]
    return testDict

def sortDict(testDict):
    for item in testDict:
        sorted_list = sorted(testDict[item], key=itemgetter(1), reverse=True)
        testDict[item] = sorted_list
    return testDict

def createPerformanceFile(testDict, fold_num):
    with open(f'trainingperformance_fold{fold_num}.txt', 'w') as f:
        for qid in testDict:
            rank = 0
            for docid, score in testDict[qid]:
                rank += 1
                if rank <= 100:
                    f.write("%s Q0 %s %d %f Exp\n" % (qid, docid, rank, score))

def main():
    print("Reading feature matrix...")
    
    # Read CSV - use pandas
    df = pd.read_csv('staticFeatureMatrix.csv')
    
    # Convert QID-DocID to regular Python list of strings - THIS IS CRITICAL
    qdID_raw = df['QID-DocID'].values
    qdID = [str(x) for x in qdID_raw]  # Convert each element to regular string
    
    # Features
    feature_names = ['TF-IDF', 'Okapi TF', 'BM25', 'Laplace', 'Jelinek-Mercer']
    X = df[feature_names].values
    Y = df['Label'].values
    
    print(f"Loaded {len(X)} samples with {X.shape[1]} features")
    print(f"Labels range: {Y.min()} to {Y.max()}")
    print(f"Example QID-DocID: {qdID[0]}")
    print(f"Type of QID-DocID[0]: {type(qdID[0])}")
    
    # 5-fold cross validation
    kfold = model_selection.KFold(n_splits=5, random_state=42, shuffle=True)
    
    fold_num = 1
    all_predictions = []
    all_actual = []
    
    for train_index, test_index in kfold.split(X, Y):
        print(f"\nFold {fold_num}/5")
        print(f"  Training samples: {len(train_index)}")
        print(f"  Test samples: {len(test_index)}")
        
        X_train, X_test = X[train_index], X[test_index]
        Y_train, Y_test = Y[train_index], Y[test_index]
        
        # Get training QID-DocID as regular list
        qdID_train = [qdID[i] for i in train_index]
        
        # Train Linear Regression
        regr = linear_model.LinearRegression()
        regr.fit(X_train, Y_train)
        
        # Print learned coefficients
        coeff_dict = dict(zip(feature_names, regr.coef_))
        print(f"  Coefficients: {coeff_dict}")
        print(f"  Intercept: {regr.intercept_:.4f}")
        
        # Predict
        predictions = regr.predict(X_train)
        
        # Store
        all_predictions.extend(predictions)
        all_actual.extend(Y_train)
        
        # Create results
        testDict = createDict(qdID_train, predictions)
        testDict = sortDict(testDict)
        createPerformanceFile(testDict, fold_num)
        
        fold_num += 1
    
    # Combine all fold results
    print("\nCombining all fold results...")
    combined_dict = {}
    
    for fold in range(1, 6):
        filename = f'trainingperformance_fold{fold}.txt'
        try:
            with open(filename, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 6:
                        qid = parts[0]
                        docid = parts[2]
                        score = float(parts[4])
                        if qid not in combined_dict:
                            combined_dict[qid] = []
                        combined_dict[qid].append((docid, score))
        except FileNotFoundError:
            print(f"  Warning: {filename} not found")
    
    # Write combined results
    if combined_dict:
        with open('trainingperformance.txt', 'w') as f:
            for qid in sorted(combined_dict.keys(), key=lambda x: int(x) if x.isdigit() else 0):
                sorted_results = sorted(combined_dict[qid], key=itemgetter(1), reverse=True)
                for rank, (docid, score) in enumerate(sorted_results[:100], 1):
                    f.write("%s Q0 %s %d %f Exp\n" % (qid, docid, rank, score))
        print("Created trainingperformance.txt")
    else:
        print("Error: No results to combine!")
    
    # Calculate performance
    if all_predictions:
        from sklearn.metrics import mean_squared_error, r2_score
        mse = mean_squared_error(all_actual, all_predictions)
        r2 = r2_score(all_actual, all_predictions)
        print(f"\nOverall Model Performance:")
        print(f"  Mean Squared Error: {mse:.4f}")
        print(f"  R-squared Score: {r2:.4f}")
    
    print("\nDone!")

if __name__ == "__main__":
    main()