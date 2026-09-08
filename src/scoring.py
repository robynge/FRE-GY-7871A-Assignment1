"""Dictionary proportions and Loughran–McDonald equation (1).

IDF is fitted on exactly the documents passed to score_corpus. Refit whenever
the estimation sample changes. Weighted scores are sums, not proportions.
"""
from collections import Counter
import math
import pandas as pd


def score_corpus(documents, lexicons):
    documents = list(documents)
    if not documents:
        raise ValueError("Cannot score an empty corpus")
    if any(not d or any(n <= 0 for n in d.values()) for d in documents):
        raise ValueError("Each document must have positive word counts")
    df = Counter(w for document in documents for w in document)
    n_documents = len(documents)
    rows = []
    for counts in documents:
        total = sum(counts.values())
        denominator = 1 + math.log(total / len(counts))
        row = {"n_words": total, "n_distinct": len(counts)}
        for category, words in lexicons.items():
            hits = {w: count for w, count in counts.items() if w in words}
            row[category + "_prop"] = sum(hits.values()) / total
            row[category + "_tfidf"] = sum(
                (1 + math.log(count)) / denominator * math.log(n_documents / df[w])
                for w, count in hits.items()
            )
        rows.append(row)
    return pd.DataFrame(rows)


def common_words(documents, lexicons, limit=30):
    counts = Counter()
    for document in documents:
        counts.update(document)
    rows = []
    for category, words in lexicons.items():
        hits = Counter({w: counts[w] for w in words if counts[w]})
        total = sum(hits.values())
        for rank, (word, count) in enumerate(hits.most_common(limit), 1):
            rows.append({"category": category, "rank": rank, "word": word,
                         "count": count, "share_pct": 100 * count / total})
    return pd.DataFrame(rows)
