import unittest
from pydub import AudioSegment
from pydub.generators import WhiteNoise
from ClassyFlaskDB.new.SQLStorageEngine import *
from ClassyFlaskDB.DefaultModel import get_local_time
from ClassyFlaskDB.new.AudioTranscoder import AudioTranscoder
import tempfile
import os

class AudioTranscoderTests(unittest.TestCase):
    def test_audio_transcoder(self):
        DATA = DATADecorator()

        @DATA
        @dataclass
        class AudioObject:
            name: str
            audio: AudioSegment

        # Create a temporary directory for the database and audio files
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            files_dir = os.path.join(tmpdir, 'audio_files')
            
            data_engine = SQLStorageEngine(f"sqlite:///{db_path}", DATA, files_dir=files_dir)

            # Generate some noise
            noise_duration_ms = 314 #.314 seconds
            noise = WhiteNoise().to_audio_segment(duration=noise_duration_ms)

            # Create and merge object
            audio_obj = AudioObject(name="Test Noise", audio=noise)
            data_engine.merge(audio_obj)

            # Query from database
            queried_obj = data_engine.query(AudioObject).filter_by_id(audio_obj.get_primary_key())

            # Validate
            self.assertEqual(queried_obj.name, "Test Noise")
            self.assertIsNotNone(queried_obj.audio)
            self.assertAlmostEqual(len(queried_obj.audio), noise_duration_ms, delta=2)
            
            # Check if the audio has non-zero amplitude
            self.assertGreater(queried_obj.audio.rms, 0)

            # Verify that the audio file exists in the files directory
            audio_files = os.listdir(files_dir)
            self.assertEqual(len(audio_files), 1)
            self.assertTrue(audio_files[0].endswith('.mp3'))

if __name__ == '__main__':
    unittest.main()