from unittest2 import TestCase
from couchdbkit.schema import Document
from .mock_couch import MockCouchDb


class Test(TestCase):
    def test_mock_couch_view(self):
        db = MockCouchDb(views={
            'my/view': [
                (
                    {'reduce': True, 'group': True, 'startkey': [], 'endkey': [{}]},
                    [
                        {'r': 'result1'},
                        {'r': 'result2'},
                    ]
                )
            ]
        })

        result = db.view("my/view", startkey=[], endkey=[{}], group=True, reduce=True)
        self.assertEqual(2, result.total_rows)
        self.assertEqual([{'r': 'result1'}, {'r': 'result2'}], result.rows)

    def test_mock_couch_doc_get(self):
        db = MockCouchDb(docs={
            "123": {'d': 1},
            "124": {'d': 2}
        })

        result = db.get("123")
        self.assertEqual({"d": 1}, result)

        result = db.get("124", wrapper=lambda x: x['d'])
        self.assertEqual(2, result)

    def test_mock_couch_doc_save(self):
        db = MockCouchDb()

        class MockDoc(Document):
            _db = db
            _doc_type = "Mock"

        doc = MockDoc(_id="1")
        doc.save()

        self.assertEqual({'doc_type': 'MockDoc', '_id': '1'}, db.mock_docs["1"])