"""A tiny fake of the Supabase client so API tests never touch the real database."""
from types import SimpleNamespace


class FakeQuery:
    """Accepts any chained call (.select().eq().order()...) and returns canned data."""

    def __init__(self, data, error=None):
        self._data = data
        self._error = error

    def __getattr__(self, name):
        def method(*args, **kwargs):
            return self

        return method

    def execute(self):
        if self._error:
            raise self._error
        return SimpleNamespace(data=self._data)


class FakeSupabase:
    def __init__(self):
        self.responses: dict[str, list] = {}   # table or rpc name -> rows returned
        self.errors: dict[str, Exception] = {}  # table or rpc name -> exception to raise

    def table(self, name):
        return FakeQuery(self.responses.get(name, []), self.errors.get(name))

    def rpc(self, name, params=None):
        return FakeQuery(self.responses.get(name, []), self.errors.get(name))
