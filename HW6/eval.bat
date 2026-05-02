@echo off
cd /d C:\Users\hp\Downloads\Information-retrieval-system\HW6

echo ================================================================================
echo HW6 - MODEL EVALUATION RESULTS
echo ================================================================================
echo.

echo [1/6] ML COMBINED MODEL (trainingperformance.txt)
echo ================================================================================
python Trec_Eval.py cranqrel trainingperformance.txt
echo.

echo [2/6] BM25
echo ================================================================================
if exist "OkapiBM25_Results_File.txt" (
    python Trec_Eval.py cranqrel OkapiBM25_Results_File.txt
) else if exist "..\hw1_result\OkapiBM25_Results_File.txt" (
    python Trec_Eval.py cranqrel ..\hw1_result\OkapiBM25_Results_File.txt
) else (
    echo File not found!
)
echo.

echo [3/6] TF-IDF
echo ================================================================================
if exist "TF-IDF_Results_File.txt" (
    python Trec_Eval.py cranqrel TF-IDF_Results_File.txt
) else if exist "..\hw1_result\TF-IDF_Results_File.txt" (
    python Trec_Eval.py cranqrel ..\hw1_result\TF-IDF_Results_File.txt
) else (
    echo File not found!
)
echo.

echo [4/6] OKAPI TF
echo ================================================================================
if exist "OkapiTF_Results_File.txt" (
    python Trec_Eval.py cranqrel OkapiTF_Results_File.txt
) else if exist "..\hw1_result\OkapiTF_Results_File.txt" (
    python Trec_Eval.py cranqrel ..\hw1_result\OkapiTF_Results_File.txt
) else (
    echo File not found!
)
echo.

echo [5/6] LAPLACE LM
echo ================================================================================
if exist "UnigramLMLaplace_Results_File.txt" (
    python Trec_Eval.py cranqrel UnigramLMLaplace_Results_File.txt
) else if exist "..\hw1_result\UnigramLMLaplace_Results_File.txt" (
    python Trec_Eval.py cranqrel ..\hw1_result\UnigramLMLaplace_Results_File.txt
) else (
    echo File not found!
)
echo.

echo [6/6] JELINEK-MERCER LM
echo ================================================================================
if exist "UnigramLMJM_Results_File.txt" (
    python Trec_Eval.py cranqrel UnigramLMJM_Results_File.txt
) else if exist "..\hw1_result\UnigramLMJM_Results_File.txt" (
    python Trec_Eval.py cranqrel ..\hw1_result\UnigramLMJM_Results_File.txt
) else (
    echo File not found!
)
echo.

echo ================================================================================
echo OPTIONAL - INDIVIDUAL FOLD RESULTS
echo ================================================================================
echo.
echo ML Fold 1:
python Trec_Eval.py cranqrel trainingperformance_fold1.txt 2>nul || echo Not available
echo.
echo ML Fold 2:
python Trec_Eval.py cranqrel trainingperformance_fold2.txt 2>nul || echo Not available
echo.
echo ML Fold 3:
python Trec_Eval.py cranqrel trainingperformance_fold3.txt 2>nul || echo Not available
echo.
echo ML Fold 4:
python Trec_Eval.py cranqrel trainingperformance_fold4.txt 2>nul || echo Not available
echo.
echo ML Fold 5:
python Trec_Eval.py cranqrel trainingperformance_fold5.txt 2>nul || echo Not available

echo.
echo ================================================================================
echo SUMMARY - Look for "Average Precision" values above
echo ================================================================================
echo.
echo The ML Combined Model should have the highest Average Precision
echo Higher number = Better model
echo ================================================================================
pause