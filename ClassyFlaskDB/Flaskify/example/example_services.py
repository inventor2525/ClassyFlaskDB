from pydub import AudioSegment
from ClassyFlaskDB.Flaskify.Route import Route

class MyService:
    @Route(path='/process_audio', methods=['POST'])
    def process_audio(self, text: str, audio: AudioSegment) -> str:
        # Dummy implementation
        return f"Processed text: {text} and audio length: {len(audio)} ms"

    @Route()
    def reverse_text(self, text: str) -> str:
        return text[::-1]

    @Route("/text_length_______blaaaah")
    def text_length(self, text: str) -> int:
        return len(text)

    @Route("/concatenate_texts")
    def concatenate_texts(self, text1: str, text2: str) -> str:
        return text1 + text2

class AnotherService:
    @Route()
    @staticmethod
    def add_numbers(num1: int, num2: int) -> int:
        return num1 + num2

    @Route()
    def multiply_numbers(self, num1: int, num2: int) -> int:
        return num1 * num2

    @Route()
    def upper_case_text(self, text: str) -> str:
        return text.upper()

    @Route()
    def repeat_text(self, text: str, times: int) -> str:
        return text * times
print("Hello World")