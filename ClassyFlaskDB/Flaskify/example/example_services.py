from pydub import AudioSegment

class MyService:
    def process_audio(self, text: str, audio: AudioSegment) -> str:
        # Dummy implementation
        return f"Processed text: {text} and audio length: {len(audio)} ms"

    def reverse_text(self, text: str) -> str:
        return text[::-1]

    def text_length(self, text: str) -> int:
        return len(text)

    def concatenate_texts(self, text1: str, text2: str) -> str:
        return text1 + text2

class AnotherService:
    def add_numbers(self, num1: int, num2: int) -> int:
        return num1 + num2

    def multiply_numbers(self, num1: int, num2: int) -> int:
        return num1 * num2

    def upper_case_text(self, text: str) -> str:
        return text.upper()

    def repeat_text(self, text: str, times: int) -> str:
        return text * times