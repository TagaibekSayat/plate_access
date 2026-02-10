import time

def is_complete_plate(plate: str) -> bool:
    if not plate:
        return False
    if len(plate) < 7:
        return False
    if not any(c.isalpha() for c in plate):
        return False
    if sum(c.isdigit() for c in plate) < 2:
        return False
    return True


class PlateStability:
    def __init__(self, frames_required=7, cooldown=5, min_visible_time=1.0):
        self.frames_required = frames_required
        self.cooldown = cooldown
        self.min_visible_time = min_visible_time

        self.counter = {}
        self.first_seen = {}
        self.last_access = {}

    def update(self, plate):
        now = time.time()

        # ❌ Жарты номерді бірден reject
        if not is_complete_plate(plate):
            return None

        # ❄️ Cooldown
        if plate in self.last_access:
            if now - self.last_access[plate] < self.cooldown:
                return None

        # ⏱ Бірінші көрінген уақыт
        if plate not in self.first_seen:
            self.first_seen[plate] = now

        # 🧮 Кадр санау
        self.counter[plate] = self.counter.get(plate, 0) + 1

        # ⏱ Уақыт + кадр шарты
        if (
            self.counter[plate] >= self.frames_required
            and now - self.first_seen[plate] >= self.min_visible_time
        ):
            self.counter.clear()
            self.first_seen.clear()
            self.last_access[plate] = now
            return plate

        return None
