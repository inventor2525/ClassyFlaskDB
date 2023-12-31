from pydub import AudioSegment
from ClassyFlaskDB.Flaskify import Route, StaticRoute, Flaskify

@Flaskify
class MyService:
    @Route
    @staticmethod
    def get_audio(path: str) -> AudioSegment:
        return AudioSegment.from_file(path, format="mp3")
    
    @Route(path='/process_audio', methods=['POST'])
    @staticmethod
    def process_audio(text: str, audio: AudioSegment) -> str:
        # Dummy implementation
        return f"Processed text: {text} and audio length: {len(audio)} ms"

    @StaticRoute
    def reverse_text(text: str) -> str:
        return text[::-1]

    @StaticRoute("/text_length_______blaaaah")
    def text_length(text: str) -> int:
        return len(text)

    @Route("/concatenate_texts")
    @staticmethod
    def concatenate_texts(text1: str, text2: str) -> str:
        return text1 + text2

@Flaskify("another")
class AnotherService:
    @Route
    @staticmethod
    def add_numbers(num1: int, num2: int) -> int:
        return num1 + num2

    @Route()
    @staticmethod
    def multiply_numbers(num1: int, num2: int) -> int:
        return num1 * num2

    @Route
    @staticmethod
    def upper_case_text(text: str) -> str:
        return text.upper()

    @Route()
    @staticmethod
    def repeat_text(text: str, times: int) -> str:
        return text * times
    
from .ConversationModel import Conversation, Message, ModelSource, UserSource

@Flaskify
class ConvService:
    @StaticRoute
    def Talk(conv:Conversation) -> Conversation:
        m = Message(content="Hello from DA "+conv.message_sequence.messages[-1].content, source=ModelSource(model_name="MyModel", model_parameters={"hello":"world"}, message_sequence=conv.message_sequence))
        conv.add_message(m)
        return conv