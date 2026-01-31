import random

from src.session import TokenSession


class FakeExplorer:
    def __init__(self):
        self.prompt_text = ""
        self.prompt_tokens = []
        self.top_tokens = [
            {"token_id": 10, "token": "A", "probability": 0.7},
            {"token_id": 20, "token": "B", "probability": 0.2},
            {"token_id": 30, "token": "C", "probability": 0.1},
        ]

    def set_prompt(self, prompt_text):
        self.prompt_text = prompt_text
        if prompt_text:
            self.prompt_tokens = [int(tok) for tok in prompt_text.split()]
        else:
            self.prompt_tokens = []
        return self

    def get_prompt(self):
        return self.prompt_text

    def get_prompt_tokens(self):
        return self.prompt_tokens

    def get_prompt_tokens_strings(self):
        return [str(tok) for tok in self.prompt_tokens]

    def get_prompt_token_probabilities(self):
        return [0.5 for _ in self.prompt_tokens]

    def append_token(self, token_id):
        self.prompt_tokens.append(token_id)
        self._sync_text()
        return self

    def pop_token(self):
        if not self.prompt_tokens:
            return None
        last_token = self.prompt_tokens.pop()
        self._sync_text()
        return last_token

    def get_top_n_tokens(self, n=5, search=""):
        return self.top_tokens[:n]

    def _sync_text(self):
        self.prompt_text = " ".join(str(tok) for tok in self.prompt_tokens)


def test_add_remove_prompt_updates_index_and_prompt():
    explorer = FakeExplorer()
    session = TokenSession(explorer, prompt="1 2", tokens_to_show=3)

    assert session.prompts == ["1 2"]
    assert session.prompt_index == 0

    assert session.add_prompt(max_prompts=2) is True
    assert session.prompts == ["1 2", "1 2"]
    assert session.prompt_index == 1

    session.set_prompt_text("3 4")
    assert session.prompts[1] == "3 4"

    assert session.remove_prompt() is True
    assert session.prompts == ["1 2"]
    assert session.prompt_index == 0
    assert session.get_prompt() == "1 2"


def test_append_selected_token_resets_selection():
    explorer = FakeExplorer()
    session = TokenSession(explorer, prompt="1 2", tokens_to_show=3)

    assert session.select_next_token() is True
    assert session.selected_row == 1

    assert session.append_selected_token() is True
    assert session.selected_row == 0
    assert session.get_prompt() == "1 2 20"


def test_append_weighted_token_appends_from_displayed_tokens():
    explorer = FakeExplorer()
    rng = random.Random(123)
    session = TokenSession(explorer, prompt="5", tokens_to_show=3, rng=rng)

    before_tokens = session.get_prompt_tokens()[:]
    assert session.append_weighted_token() is True
    after_tokens = session.get_prompt_tokens()

    assert len(after_tokens) == len(before_tokens) + 1
    assert after_tokens[-1] in {10, 20, 30}


def test_pop_token_min_tokens():
    explorer = FakeExplorer()
    session = TokenSession(explorer, prompt="1 2", tokens_to_show=3)

    assert session.pop_token(min_tokens=1) is True
    assert session.get_prompt() == "1"
    assert session.pop_token(min_tokens=1) is False
