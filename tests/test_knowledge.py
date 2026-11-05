import tempfile
import unittest
from pathlib import Path

from app.knowledge import KnowledgeStore, answer, split_text


class KnowledgeTests(unittest.TestCase):
    def test_import_search_and_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "knowledge.db"
            store = KnowledgeStore(path)
            store.add("returns.md", "退货申请需要提供订单编号和商品照片。退款需要三个工作日。")
            store.add("delivery.md", "物流单号可以在订单详情查看。")
            sources = KnowledgeStore(path).search("退货需要什么材料")
            self.assertEqual(sources[0]["source"], "returns.md")
            self.assertIn("订单编号", answer("退货", sources))
            self.assertIn("[1]", answer("退货", sources))
            self.assertEqual(len(store.documents()), 2)

    def test_unknown_question_has_no_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            store = KnowledgeStore(Path(folder) / "knowledge.db")
            store.add("returns.md", "退货需要订单编号。")
            sources = store.search("quantum physics")
            self.assertEqual(sources, [])
            self.assertIn("没有找到", answer("quantum physics", sources))

    def test_chunking_and_empty_document(self):
        chunks = split_text("知识" * 600)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 450 for chunk in chunks))
        self.assertEqual(split_text("  "), [])


if __name__ == "__main__":
    unittest.main()
