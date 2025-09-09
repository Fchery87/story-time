import unittest
from audiobooker.pipeline.chunker import chunk

class TestChunker(unittest.TestCase):
    def test_chunking(self):
        long_text = "This is the first sentence. This is the second sentence. " \
                    "Here is a third, slightly longer sentence. And a fourth. " \
                    "Finally, the fifth sentence concludes this paragraph."

        max_chars = 100
        chunks = chunk(long_text, max_chars=max_chars)

        # Check that we got more than one chunk
        self.assertTrue(len(chunks) > 1)

        # Check that no chunk exceeds the max length
        for c in chunks:
            self.assertTrue(len(c) <= max_chars)

        # Check that the total content is preserved
        original_text_no_space = "".join(long_text.split())
        chunked_text_no_space = "".join("".join(c.split()) for c in chunks)
        self.assertEqual(original_text_no_space, chunked_text_no_space)

    def test_single_long_sentence(self):
        long_sentence = "This is a single very long sentence that is designed to be longer than the max_chars limit to ensure it is not split."
        max_chars = 50
        chunks = chunk(long_sentence, max_chars=max_chars)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], long_sentence)

if __name__ == '__main__':
    unittest.main()
