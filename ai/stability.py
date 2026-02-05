import time

class PlateStability:
    def __init__(self, frames_required=4, cooldown=5):
        self.frames_required = frames_required
        self.cooldown = cooldown
        self.counter = {}
        self.last_access = {}

    def update(self, plate):
        now = time.time()

        if plate in self.last_access:
            if now - self.last_access[plate] < self.cooldown:
                return None

        self.counter[plate] = self.counter.get(plate, 0) + 1

        if self.counter[plate] >= self.frames_required:
            self.counter.clear()
            self.last_access[plate] = now
            return plate

        return None
