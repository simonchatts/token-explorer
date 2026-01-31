import random


class TokenSession:
    """Owns prompt state and token-selection logic independent of any UI."""

    def __init__(self, explorer, prompt="", tokens_to_show=30, rng=None):
        self.explorer = explorer
        self.tokens_to_show = tokens_to_show
        self.rng = rng or random.Random()

        self.prompts = [prompt]
        self.prompt_index = 0
        self.selected_row = 0
        self.displayed_tokens = []

        self.explorer.set_prompt(prompt)
        self._refresh_tokens()

    def _refresh_tokens(self):
        self.displayed_tokens = self.explorer.get_top_n_tokens(n=self.tokens_to_show)
        self.selected_row = 0
        return self.displayed_tokens

    def set_prompt_text(self, prompt_text):
        self.explorer.set_prompt(prompt_text)
        self.prompts[self.prompt_index] = self.explorer.get_prompt()
        return self._refresh_tokens()

    def add_prompt(self, max_prompts=None):
        if max_prompts is not None and len(self.prompts) >= max_prompts:
            return False
        self.prompts.append(self.explorer.get_prompt())
        self.prompt_index = (self.prompt_index + 1) % len(self.prompts)
        self.explorer.set_prompt(self.prompts[self.prompt_index])
        self._refresh_tokens()
        return True

    def remove_prompt(self):
        if len(self.prompts) <= 1:
            return False
        self.prompts.pop(self.prompt_index)
        self.prompt_index = (self.prompt_index - 1) % len(self.prompts)
        self.explorer.set_prompt(self.prompts[self.prompt_index])
        self._refresh_tokens()
        return True

    def increment_prompt(self):
        self.prompt_index = (self.prompt_index + 1) % len(self.prompts)
        self.explorer.set_prompt(self.prompts[self.prompt_index])
        self._refresh_tokens()

    def decrement_prompt(self):
        self.prompt_index = (self.prompt_index - 1) % len(self.prompts)
        self.explorer.set_prompt(self.prompts[self.prompt_index])
        self._refresh_tokens()

    def select_next_token(self):
        if self.selected_row < len(self.displayed_tokens) - 1:
            self.selected_row += 1
            return True
        return False

    def select_prev_token(self):
        if self.selected_row > 0:
            self.selected_row -= 1
            return True
        return False

    def append_selected_token(self):
        if not self.displayed_tokens:
            return False
        token = self.displayed_tokens[self.selected_row]
        self.explorer.append_token(token["token_id"])
        self.prompts[self.prompt_index] = self.explorer.get_prompt()
        self._refresh_tokens()
        return True

    def append_weighted_token(self):
        if not self.displayed_tokens:
            return False
        weights = [token["probability"] for token in self.displayed_tokens]
        if not any(weight > 0 for weight in weights):
            return False
        chosen_token = self.rng.choices(self.displayed_tokens, weights=weights, k=1)[0]
        self.explorer.append_token(chosen_token["token_id"])
        self.prompts[self.prompt_index] = self.explorer.get_prompt()
        self._refresh_tokens()
        return True

    def pop_token(self, min_tokens=1):
        if len(self.explorer.get_prompt_tokens()) <= min_tokens:
            return False
        self.explorer.pop_token()
        self.prompts[self.prompt_index] = self.explorer.get_prompt()
        self._refresh_tokens()
        return True

    def get_prompt(self):
        return self.explorer.get_prompt()

    def get_prompt_tokens(self):
        return self.explorer.get_prompt_tokens()

    def get_prompt_tokens_strings(self):
        return self.explorer.get_prompt_tokens_strings()

    def get_prompt_token_probabilities(self):
        return self.explorer.get_prompt_token_probabilities()
