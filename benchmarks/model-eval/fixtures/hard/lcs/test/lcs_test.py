import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from lcs import lcs_length as f
class T(unittest.TestCase):
    def test_basic(self): self.assertEqual(f("abcde","ace"), 3)
    def test_none(self): self.assertEqual(f("abc","def"), 0)
    def test_empty(self): self.assertEqual(f("","abc"), 0)
    def test_same(self): self.assertEqual(f("abc","abc"), 3)
    def test_classic(self): self.assertEqual(f("AGGTAB","GXTXAYB"), 4)
if __name__ == "__main__": unittest.main()
