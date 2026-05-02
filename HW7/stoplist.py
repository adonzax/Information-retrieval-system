# create_stoplist.py
import os

# Create directory
os.makedirs('/', exist_ok=True)

# Simple stopwords list
stopwords = [
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
    'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
    'to', 'was', 'were', 'will', 'with', 'i', 'you', 'we', 'they',
    'this', 'that', 'these', 'those', 'am', 'do', 'does', 'did',
    'have', 'having', 'can', 'could', 'would', 'should', 'up', 'down',
    'out', 'off', 'over', 'under', 'again', 'then', 'once', 'here',
    'there', 'all', 'any', 'both', 'each', 'few', 'more', 'most',
    'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
    'same', 'so', 'than', 'too', 'very', 'just', 'now', 'into'
]

with open('stoplist.txt', 'w') as f:
    for word in stopwords:
        f.write(word + '\n')

print(f"✅ Created stoplist with {len(stopwords)} words")