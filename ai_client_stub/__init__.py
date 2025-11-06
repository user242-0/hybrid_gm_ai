api_key = None


class _DummyMessage:
    def __init__(self, content: str = ""):
        self.content = content


class _DummyChoice:
    def __init__(self, content: str = ""):
        self.message = _DummyMessage(content)


class _DummyCompletions:
    def create(self, *args, **kwargs):
        return type("Response", (), {"choices": [_DummyChoice("")]})()


class _DummyChat:
    def __init__(self):
        self.completions = _DummyCompletions()


chat = _DummyChat()