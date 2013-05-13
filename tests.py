from unittest2 import TestCase
from couchdbkit.schema import Document
from datetime import date

import fakecouch


class Test(TestCase):
    def test_mock_couch_view(self):
        db = fakecouch.FakeCouchDb(views={
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

    def test_mock_couch_view_illegal_params(self):
        db = fakecouch.FakeCouchDb()
        with self.assertRaises(TypeError):
            db.view("my/view", startkey=[date(2012, 9, 1)], endkey=[date(2012, 10, 1), {}])

    def test_mock_couch_doc_get(self):
        db = fakecouch.FakeCouchDb(docs={
            "123": {'d': 1},
            "124": {'d': 2}
        })

        result = db.get("123")
        self.assertEqual({"d": 1}, result)

        result = db.get("124", wrapper=lambda x: x['d'])
        self.assertEqual(2, result)

    def test_mock_couch_doc_save(self):
        db = fakecouch.FakeCouchDb()

        class MockDoc(Document):
            _db = db
            _doc_type = "Mock"

        doc = MockDoc(_id="1")
        doc.save()

        self.assertEqual({'doc_type': 'MockDoc', '_id': '1'}, db.mock_docs["1"])
