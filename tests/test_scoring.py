from collections import Counter
import numpy as np
import pytest
from src.scoring import score_corpus


def test_assignment_equation_one_reference_values():
    docs = [Counter(x.split()) for x in ["LOSS LOSS RISK GAIN", "LOSS GAIN GAIN", "RISK RISK RISK GAIN"]]
    scores = score_corpus(docs, {"tone": {"LOSS", "RISK"}})
    np.testing.assert_allclose(scores.tone_prop, [.75, 1/3, .75])
    np.testing.assert_allclose(scores.tone_tfidf, [.8480, .2885, .5026], atol=.00005)


def test_ubiquitous_words_have_zero_idf_and_absent_words_zero_weight():
    scores = score_corpus([Counter(A=10), Counter(A=1, B=1)], {"tone": {"A", "MISSING"}})
    assert (scores.tone_tfidf == 0).all()


def test_refitting_changes_idf_when_sample_changes():
    docs = [Counter(A=1, B=1), Counter(B=3)]
    assert score_corpus(docs, {"tone": {"A"}}).tone_tfidf.iloc[0] > 0
    assert score_corpus(docs[:1], {"tone": {"A"}}).tone_tfidf.iloc[0] == 0


def test_empty_document_rejected():
    with pytest.raises(ValueError):
        score_corpus([Counter()], {"tone": {"A"}})
