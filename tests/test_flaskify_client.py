import unittest
from ClassyFlaskDB.Flaskify.example.example_client import ClientifiedMyService

class TestClient(unittest.TestCase):
    def setUp(self):
        self.client = ClientifiedMyService()

    def test_reverse_text(self):
        response = self.client.reverse_text("hello")
        self.assertEqual(response, "olleh")

if __name__ == '__main__':
    unittest.main()