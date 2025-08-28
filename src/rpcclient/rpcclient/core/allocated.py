from abc import abstractmethod


class Allocated:
    """ resource allocated on remote host that needs to be free """

    def __init__(self):
        self._deallocated = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.deallocate()

    @abstractmethod
    def _deallocate(self):
        pass

    def deallocate(self):
        if not self._deallocated:
            self._deallocated = True
            self._deallocate()
