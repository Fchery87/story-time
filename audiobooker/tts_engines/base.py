from abc import ABC, abstractmethod

class TTSEngine(ABC):
    @abstractmethod
    def synthesize(self, text, output_path):
        pass
