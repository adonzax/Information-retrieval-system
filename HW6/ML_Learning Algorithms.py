import pandas as pd
import numpy as np
from sklearn import model_selection
from sklearn import linear_model
from operator import itemgetter

def createDict(qdIDTest, predictions):
    """Convert qdIDTest list and predictions into query-document dictionary"""
    testDict = {}
    
    # Ensure qdIDTest is a regular list of strings
    qdID_list = []
    for item in qdIDTest:
        qdID_list.append(str(item))
    
    for i, prediction in enumerate(predictions):
        if i >= len(qdID_list):
            break
            
        qdIDVal = qdID_list[i]
        
        if '-' in qdIDVal:
            parts = qdIDVal.split('-', 1)
            qID = parts[0]
            docID = parts[1]
            
            if qID not in testDict:
                testDict[qID] = []
            testDict[qID].append((docID, prediction))
    
    return testDict

def sortDict(testDict):
    """Sort results by score descending"""
    for qid in testDict:
        testDict[qid] = sorted(testDict[qid], key=itemgetter(1), reverse=True)
    return testDict

def createPerformanceFile(testDict, fold_num):
    """Write TREC format results file"""
    filename = f'trainingperformance_fold{fold_num}.txt'
    with open(filename, 'w') as f:
        for qid in testDict:
            for rank, (docid, score) in enumerate(testDict[qid][:100], 1):
                f.write("%s Q0 %s %d %f Exp\n" % (qid, docid, rank, score))

def main():
    print("Reading feature matrix...")
    
    # Read CSV
    df = pd.read_csv('staticFeatureMatrix.csv')
    
    # Convert QID-DocID to regular Python list of strings - KEY FIX
    qdID_list = [str(x) for x in df['QID-DocID'].values]
    
    # Features (the 5 model scores)
    feature_names = ['TF-IDF', 'Okapi TF', 'BM25', 'Laplace', 'Jelinek-Mercer']
    X = df[feature_names].values.astype(float)
    Y = df['Label'].values.astype(float)
    
    print(f"Loaded {len(X)} samples with {X.shape[1]} features")
    print(f"Labels range: {Y.min()} to {Y.max()}")
    print(f"Example QID-DocID: {qdID_list[0]}")
    print(f"Type check: {type(qdID_list[0])}")
    
    # Filter out negative labels (optional - comment out if you want to keep them)
    # mask = Y >= 0
    # X = X[mask]
    # Y = Y[mask]
    # qdID_list = [qdID_list[i] for i in range(len(qdID_list)) if mask[i]]
    # print(f"After filtering negative labels: {len(X)} samples")
    
    # 5-fold cross validation
    kfold = model_selection.KFold(n_splits=5, random_state=42, shuffle=True)
    
    fold_num = 1
    all_predictions = []
    all_actual = []
    all_coeffs = []
    
    for train_index, test_index in kfold.split(X, Y):
        print(f"\nFold {fold_num}/5")
        print(f"  Training samples: {len(train_index)}")
        print(f"  Test samples: {len(test_index)}")
        
        # Split data
        X_train, X_test = X[train_index], X[test_index]
        Y_train, Y_test = Y[train_index], Y[test_index]
        
        # Get QID-DocID for training using regular list indexing
        qdID_train = [qdID_list[i] for i in train_index]
        
        # Train Linear Regression
        regr = linear_model.LinearRegression()
        regr.fit(X_train, Y_train)
        
        # Store coefficients
        all_coeffs.append(regr.coef_)
        
        # Print coefficients
        coeff_dict = dict(zip(feature_names, regr.coef_))
        print(f"  Coefficients: {coeff_dict}")
        print(f"  Intercept: {regr.intercept_:.4f}")
        
        # Predict on training set
        predictions = regr.predict(X_train)
        
        # Store for overall metrics
        all_predictions.extend(predictions)
        all_actual.extend(Y_train)
        
        # Create results dictionary and write file
        testDict = createDict(qdID_train, predictions)
        testDict = sortDict(testDict)
        createPerformanceFile(testDict, fold_num)
        
        fold_num += 1
    
    # Calculate average coefficients
    avg_coeffs = np.mean(all_coeffs, axis=0)
    print(f"\nAverage Coefficients across all folds:")
    for name, coeff in zip(feature_names, avg_coeffs):
        print(f"  {name}: {coeff:.4f}")
    
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
            print(f"  Loaded fold {fold}")
        except FileNotFoundError:
            print(f"  Warning: {filename} not found")
            continue
    
    # Write combined results
    if combined_dict:
        with open('trainingperformance.txt', 'w') as f:
            for qid in sorted(combined_dict.keys(), key=lambda x: int(x) if x.isdigit() else 0):
                # Remove duplicates (keep highest score per document)
                doc_scores = {}
                for docid, score in combined_dict[qid]:
                    if docid not in doc_scores or score > doc_scores[docid]:
                        doc_scores[docid] = score
                
                sorted_results = sorted(doc_scores.items(), key=itemgetter(1), reverse=True)
                for rank, (docid, score) in enumerate(sorted_results[:100], 1):
                    f.write("%s Q0 %s %d %f Exp\n" % (qid, docid, rank, score))
        print("Created trainingperformance.txt")
    else:
        print("Error: No results to combine!")
    
    # Calculate overall performance metrics
    if all_predictions:
        from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
        mse = mean_squared_error(all_actual, all_predictions)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(all_actual, all_predictions)
        r2 = r2_score(all_actual, all_predictions)
        
        print(f"\nOverall Model Performance (on training data):")
        print(f"  Mean Squared Error (MSE): {mse:.4f}")
        print(f"  Root Mean Squared Error (RMSE): {rmse:.4f}")
        print(f"  Mean Absolute Error (MAE): {mae:.4f}")
        print(f"  R-squared Score: {r2:.4f}")
    
    print("\n" + "="*50)
    print("Done! Results saved to:")
    print("  - trainingperformance_fold1.txt through trainingperformance_fold5.txt")
    print("  - trainingperformance.txt (combined)")
    print("="*50)

if __name__ == "__main__":
    main()