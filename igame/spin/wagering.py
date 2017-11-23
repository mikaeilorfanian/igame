from redis.fake_redis import fake_redis

class MoneySpentForWagering:

    redis = fake_redis

    def __init__(self, user_id):
        self.user_id = user_id

    def set(self, amount):
        self.redis.set(self.key, amount)

    def increase(self, amount):
        self.redis.incr(self.key, amount)

    def decrease(self, amount):
        self.redis.decr(self.key, amount)

    @property
    def total(self):
        total = self.redis.get(self.key)

        if total is None:
            total = self.calculate_total()
            self.set(total)

        return total

    @property
    def key(self):
        return 'money_spent:{}'.format(self.user_id)

    def calculate_total(self):
        raise NotImplementedError
