from pydub import AudioSegment
from ClassyFlaskDB.Flaskify.Route import Route

class MyService:
    @Route(path='/process_audio', methods=['POST'])
    @staticmethod
    def process_audio(text: str, audio: AudioSegment) -> str:
        # Dummy implementation
        return f"Processed text: {text} and audio length: {len(audio)} ms"

    @Route()
    @staticmethod
    def reverse_text(text: str) -> str:
        return text[::-1]

    @Route("/text_length_______blaaaah")
    @staticmethod
    def text_length(text: str) -> int:
        return len(text)

    @Route("/concatenate_texts")
    @staticmethod
    def concatenate_texts(text1: str, text2: str) -> str:
        return text1 + text2

class AnotherService:
    @Route()
    @staticmethod
    def add_numbers(num1: int, num2: int) -> int:
        return num1 + num2

    @Route()
    @staticmethod
    def multiply_numbers(num1: int, num2: int) -> int:
        return num1 * num2

    @Route()
    @staticmethod
    def upper_case_text(text: str) -> str:
        return text.upper()

    @Route()
    @staticmethod
    def repeat_text(text: str, times: int) -> str:
        return text * times
print("Hello World")