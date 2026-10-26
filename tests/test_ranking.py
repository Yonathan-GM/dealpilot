from app.services.ranking import build_keyword_query, reciprocal_rank_fusion


def test_keyword_query_joins_words_with_or():
    assert build_keyword_query("plastic pallets") == "plastic or pallets"


def test_keyword_query_keeps_product_codes_and_drops_punctuation():
    query = build_keyword_query("Is SF-500-23 film UV stable?")
    assert "SF-500-23" in query
    assert "?" not in query


def test_keyword_query_removes_duplicates_and_the_word_or():
    assert build_keyword_query("pallet or Pallet or crate") == "pallet or crate"


def test_keyword_query_empty_input():
    assert build_keyword_query("???") == ""


def test_rrf_rewards_items_found_by_both_searches():
    vector = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    keyword = [{"id": "c"}, {"id": "a"}]
    fused = reciprocal_rank_fusion([vector, keyword])
    assert [item["id"] for item in fused][:2] == ["a", "c"]  # in both lists
    assert fused[-1]["id"] == "b"                            # in only one list


def test_rrf_adds_a_score_and_keeps_original_fields():
    fused = reciprocal_rank_fusion([[{"id": "a", "content": "hello"}]])
    assert fused[0]["content"] == "hello"
    assert fused[0]["score"] > 0


def test_rrf_handles_empty_lists():
    assert reciprocal_rank_fusion([[], []]) == []
