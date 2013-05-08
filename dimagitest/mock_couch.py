from couchdbkit import ResourceNotFound

# This import pattern supports Python 2 and 3
try:
    from urllib.request import urlopen
    from urllib.parse import urlparse, urlencode
except ImportError:
    from urlparse import urlparse
    from urllib import urlopen, urlencode


class MockCouchDb(object):
    """
    An in-memory mock of CoucDB, instantiated with a simple mapping
    of resource and params to results.

    mc = MockCouchDb({
        'views': {
            'my/view': [
                (
                    {'startkey': ['j'], 'endkey': ['j', {}], reduce=True},
                    [
                       ... result objects ...
                    ]
                ),
            ],
        },
        'docs': {
            'my_doc_id': { ... doc object ...}
        }
    })

    doc = MyDoc()
    doc.save()

    mc.mock_docs[doc['_id']] == doc
    """
    def __init__(self, mock_data):
        if 'views' in mock_data:
            self.view_mock = dict([(resource, dict([(urlencode(params), result) for params, result in resource_results]))
                              for resource, resource_results in mock_data['views'].items()])

        if 'docs' in mock_data:
            self.mock_docs = mock_data['docs']

    def view(self, view_name, schema=None, wrapper=None, **params):
        return MockResult(self.view_mock[view_name][urlencode(params)])

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

    @property
    def total_rows(self):
        return len(self.rows)

    def __iter__(self):
        return iter(self.rows)
