import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dijkstra import shortest_path as sp
class T(unittest.TestCase):
    def test_direct(self): self.assertEqual(sp(2, [(0,1,5)], 0, 1), 5)
    def test_path(self): self.assertEqual(sp(4, [(0,1,1),(1,2,2),(2,3,3),(0,3,10)], 0, 3), 6)
    def test_unreachable(self): self.assertEqual(sp(3, [(0,1,1)], 0, 2), -1)
    def test_same(self): self.assertEqual(sp(1, [], 0, 0), 0)
    def test_cheaper_indirect(self): self.assertEqual(sp(3, [(0,1,1),(1,2,1),(0,2,5)], 0, 2), 2)
if __name__ == "__main__": unittest.main()
