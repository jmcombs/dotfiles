import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ini_parse import parse_ini as p
class T(unittest.TestCase):
    def test_basic(self): self.assertEqual(p("[a]\nx=1"), {"a":{"x":"1"}})
    def test_multi(self): self.assertEqual(p("[a]\nx=1\ny=2\n[b]\nz=3"), {"a":{"x":"1","y":"2"},"b":{"z":"3"}})
    def test_comments(self): self.assertEqual(p("; c\n[a]\n# c2\nx=1"), {"a":{"x":"1"}})
    def test_whitespace(self): self.assertEqual(p("[a]\n  x =  1  "), {"a":{"x":"1"}})
    def test_equals_in_value(self): self.assertEqual(p("[a]\nx=1=2"), {"a":{"x":"1=2"}})
if __name__ == "__main__": unittest.main()
