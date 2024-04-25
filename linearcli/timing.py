from time import perf_counter
# via https://stackoverflow.com/questions/33987060/python-context-manager-that-measures-time

class timing:
    def __init__(self, name, debug=False):
        self.name = name
        self.debug = debug

    def __enter__(self):
        self.start = perf_counter()
        return self

    def __exit__(self, type, value, traceback):
        self.time = perf_counter() - self.start
        self.readout = f'{self.name} took: {self.time:.3f} seconds'
        if self.debug:
            print(self.readout)
