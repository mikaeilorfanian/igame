class FakeReadis:

    storage = {}

    def __init__(self):
        pass

    def set(self, key, value):
        self.storage[key] = value

    def get(self, key):
        return self.storage.get(key, None)


    def incr(self, key, increment_by):
        self.storage[key] += increment_by

    def decr(self, key, decrement_by):
        self.storage[key] -= decrement_by

    def clear(self):
        FakeReadis.storage = dict()


fake_redis = FakeReadis()
