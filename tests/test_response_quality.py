from api.service import RAGService


def test_citation_normalization_and_spacing():
    service = RAGService()
    answer = "Policy requires controls [Source:01_Data_Governance_Policy]."
    sources = ["01_Data_Governance_Policy"]

    normalized = service._normalize_answer_citations(answer, sources)
    assert "(Source: 01_Data_Governance_Policy)" in normalized


def test_citation_appended_when_missing():
    service = RAGService()
    answer = "Policy requires controls across enterprise data."
    sources = ["01_Data_Governance_Policy"]

    normalized = service._normalize_answer_citations(answer, sources)
    assert normalized.endswith("(Source: 01_Data_Governance_Policy)")


def test_confidence_in_expected_range():
    service = RAGService()
    contexts = [
        {"doc_id": "01_Data_Governance_Policy", "content": "Data governance policy controls.", "relevance_score": 0.7},
        {"doc_id": "05_Information_Security_Policy", "content": "Security controls and monitoring.", "relevance_score": 0.5},
    ]
    answer = "Data governance policy includes controls. (Source: 01_Data_Governance_Policy)"

    confidence = service.calculate_confidence("what is data governance policy", contexts, answer)
    assert 0.0 <= confidence <= 1.0
