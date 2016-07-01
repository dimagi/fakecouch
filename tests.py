from unittest2 import TestCase
from couchdbkit.exceptions import ResourceConflict
from couchdbkit.schema import Document
from datetime import date

import fakecouch
from fakecouch import ResourceNotFound


class Test(TestCase):
    def test_mock_couch_view(self):
        db = fakecouch.FakeCouchDb(views={
            'my/view': [
                (
                    {'reduce': True, 'group': True, 'startkey': [], 'endkey': [{}]},
                    {
                        'rows': [{'r': 'result1'}, {'r': 'result2'}]
                    }
                )
            ]
        })

        result = db.view("my/view", startkey=[], endkey=[{}], group=True, reduce=True)
        self.assertEqual(2, result.total_rows)
        self.assertEqual([{'r': 'result1'}, {'r': 'result2'}], result.all())

    def test_mock_couch_view_illegal_params(self):
        db = fakecouch.FakeCouchDb()
        with self.assertRaises(TypeError):
            db.view("my/view", startkey=[date(2012, 9, 1)], endkey=[date(2012, 10, 1), {}]).all()

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

        doc = MockDoc()
        doc.save()

        self.assertTrue(isinstance(doc._id, basestring))
        self.assertTrue(doc._id != '')
        self.assertEqual({'doc_type': 'MockDoc', '_id': doc._id, '_rev': doc._rev}, db.mock_docs[doc._id])

        db.reset()

        doc = MockDoc(_id="1")
        doc.save()

        self.assertEqual({'doc_type': 'MockDoc', '_id': '1', '_rev': doc._rev}, db.mock_docs["1"])

    def test_mock_couch_doc_delete(self):
        db = fakecouch.FakeCouchDb()

        class MockDoc(Document):
            _db = db
            _doc_type = "Mock"

        doc = MockDoc(_id='1')
        doc.save()
        result = db.get("1")
        self.assertIsNotNone(result)
        doc.delete()
        with self.assertRaises(ResourceNotFound):
            db.get("1")

    def test_saving_modified_doc(self):
        db = fakecouch.FakeCouchDb(docs={
            '123': {'_id': '123', '_rev': '123'}
        })

        with self.assertRaises(ResourceConflict):
            db.save_doc({'_id': '123', '_rev': '124'})

    def test_update_view(self):
        db = fakecouch.FakeCouchDb(views={
            'my/view': [
                (
                    {'reduce': True, 'group': True, 'startkey': [], 'endkey': [{}]},
                    {
                        'rows': [{'r': 'result1'}, {'r': 'result2'}]
                    }
                )
            ]
        })

        result = db.view("my/view", startkey=[], endkey=[{}], group=True, reduce=True)
        self.assertEqual(2, result.total_rows)

        with self.assertRaises(KeyError):
            db.update_view("another/view", [])

        fake_results = [{'id': 1, 'value': None, 'key': [1], 'doc': {}}]
        db.update_view("my/view", [({}, fake_results)])
        result = db.view("my/view")
        self.assertEqual(list(result), fake_results)
