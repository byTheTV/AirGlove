"""Practice the order of Invoker inputs using resolved gesture bindings."""

PRACTICE_KEYS = ("W", "W", "Q", "R", "E", "E", "E", "R", "F", "D")
PRACTICE_CAPTIONS = ("Wex", "Wex", "Quas", "Invoke", "Exort", "Exort", "Exort",
                     "Invoke", "Слот 2", "Слот 1")
PRACTICE_GESTURES = (3, 3, 2, 5, 4, 4, 4, 5, -2, 1)


class Training:
    def __init__(self):
        self.reset()

    def reset(self):
        self.progress = 0
        self.errors = 0
        self.start = None
        self.duration = None
        self.last = None

    def feed(self, key, now):
        if self.duration is not None:
            return
        self.last = key
        if key != PRACTICE_KEYS[self.progress]:
            self.errors += 1
            self.progress = 0
            self.start = None
            if key != PRACTICE_KEYS[0]:
                return
        if self.start is None:
            self.start = now
        self.progress += 1
        if self.progress == len(PRACTICE_KEYS):
            self.duration = now - self.start
