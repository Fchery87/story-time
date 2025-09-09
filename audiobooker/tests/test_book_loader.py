import unittest
import os
from audiobooker.utils.book_loader import load_book

class TestBookLoader(unittest.TestCase):
    def test_load_text_file(self):
        # Path to the sample text file, relative to this test file
        # This makes the test runnable from any directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sample_path = os.path.join(base_dir, '..', 'samples', 'sample.txt')

        chapters = load_book(sample_path)

        # Check that we have 2 chapters
        self.assertEqual(len(chapters), 2)

        # Check the titles
        self.assertEqual(chapters[0][0], "Chapter 1: The Beginning")
        self.assertEqual(chapters[1][0], "Chapter 2: The Middle")

        # Check that the text is not empty
        self.assertTrue(chapters[0][1])
        self.assertTrue(chapters[1][1])

if __name__ == '__main__':
    unittest.main()
