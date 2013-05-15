from couchdbkit import ResourceNotFound
from couchdbkit.resource import encode_params

# This import pattern supports Python 2 and 3
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode


class FakeCouchDb(object):
    """
    An in-memory mock of CoucDB, instantiated with a simple mapping
    of resource and params to results.

    mc = FakeCouchDb(views={
        'my/view': [
            (
                {'startkey': ['j'], 'endkey': ['j', {}], reduce=True},
                [
                   ... result objects ...
                ]
            ),
        ]},
        docs={
            'my_doc_id': { ... doc object ...}
        }
    })

    doc = MyDoc()
    doc.save()

    mc.mock_docs[doc['_id']] == doc
    """

    def __init__(self, views=None, docs=None):
        if views:
            self.view_mock = dict([
                (resource, dict([(self._param_key(params), result) for params, result in view_results]))
                for resource, view_results in views.items()])
        else:
            self.view_mock = {}

        self.mock_docs = docs or {}

    def add_view(self, name, view_results):
        self.view_mock[name] = dict([(self._param_key(params), result) for params, result in view_results])

    def _param_key(self, params):
        params = encode_params(params)
        return urlencode(sorted(params.items(), key=lambda p: p[0]))

    def view(self, view_name, schema=None, wrapper=None, **params):
        view = self.view_mock.get(view_name, {})
        return MockResult(view.get(self._param_key(params), []))

    def save_doc(self, doc, **params):
        self.mock_docs[doc["_id"]] = doc

    def get(self, docid, rev=None, wrapper=None):
        doc = self.mock_docs.get(docid, None)
        if not doc:
            raise ResourceNotFound
        elif wrapper:
            return wrapper(doc)
        else:
            return doc

    def open_doc(self, docid):
        doc = self.mock_docs.get(docid, None)
        return doc


class MockResult(object):
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    @property
    def total_rows(self):
        return len(self.rows)

    def __iter__(self):
        return iter(self.rows)
