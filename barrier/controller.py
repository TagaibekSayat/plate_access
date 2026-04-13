import time


class BarrierController:
    def __init__(self, min_open_time=10):
        self.is_opened = False
        self.opened_at = None
        self.min_open_time = min_open_time
        self.manual_open = False   
    def open(self, manual=False):
        if not self.is_opened:
            print("🚧 Шлагбаум АШЫЛДЫ")
            self.is_opened = True
            self.opened_at = time.time()
            self.manual_open = manual

    def can_close(self, car_present: bool) -> bool:
        if not self.is_opened:
            return False

        if self.manual_open:
            return False

        if car_present:
            return False

        if time.time() - self.opened_at < self.min_open_time:
            return False

        return True

    def close(self):
        if self.is_opened:
            print(" Шлагбаум ЖАБЫЛДЫ")
            self.is_opened = False
            self.opened_at = None
            self.manual_open = False

    def status(self):
        if self.is_opened and self.manual_open:
            return "MANUAL OPEN"
        if self.is_opened:
            return "OPEN"
        return "CLOSED"
