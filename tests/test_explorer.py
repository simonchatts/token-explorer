from src.explorer import Explorer

def test_get_prompt_token_probabilities():
    explorer = Explorer()
    explorer.set_prompt("Hello, world")
    probabilities = explorer.get_prompt_token_probabilities()
    assert probabilities[0] == 0.5 # first token has no context
    assert len(probabilities) == len(explorer.prompt_tokens)

def test_get_top_n_tokens():
    explorer = Explorer()
    explorer.set_prompt("Hello, world")
    tokens = explorer.get_top_n_tokens(n=5)
    assert len(tokens) == 5
    assert all("token" in token for token in tokens)
    assert all("token_id" in token for token in tokens)
    assert all("probability" in token for token in tokens)
    probabilities = [token["probability"] for token in tokens]
    assert probabilities == sorted(probabilities, reverse=True)
