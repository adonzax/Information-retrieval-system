#!/bin/bash

echo "=========================================="
echo "HW2 - Cranfield Custom Index"
echo "=========================================="

# Check if data exists
if [ ! -f "data/cran.all.1400" ]; then
    echo "ERROR: Cranfield data not found in data/"
    echo "Please place cran.all.1400, cran.qry, and cranqrel in data/"
    exit 1
fi

# Create directories
mkdir -p pickles results

# Step 1: Build index
echo ""
echo "Step 1: Building inverted index..."
python src/Cranfield_Indexer.py

# Step 2: Process queries
echo ""
echo "Step 2: Processing queries..."
python src/Cranfield_QueryProcessing.py

# Step 3: Run retrieval
echo ""
echo "Step 3: Running retrieval models..."
python src/Cranfield_RetrievalModels.py

echo ""
echo "=========================================="
echo "Done! Results saved in results/"
echo "=========================================="