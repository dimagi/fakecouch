import uuid
import logging

# this import pattern lets fakecouch not depend on couchdbkit
try:
    import couchdbkit
except ImportError:
    import json

    class ResourceNotFound(Exception):
        pass

    # copy-pasted from couchdbkit.resource
    def encode_params(params):
        """ encode parameters in json if needed """
        _params = {}
        if params:
            for name, value in params.items():
                if name in ('key', 'startkey', 'endkey'):
                    value = json.dumps(value)
                elif value is None:
                    continue
                elif not isinstance(value, basestring):
                    value = json.dumps(value)
                _params[name] = value
        return _params
else:
    from couchdbkit import ResourceNotFound
    from couchdbkit.resource import encode_params


# This import pattern supports Python 2 and 3
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode


logger = logging.getLogger(__name__)


class FakeCouchDb(object):
    """
    An in-memory mock of CouchDB, instantiated with a simple mapping
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

    def reset(self):
        logger.info('Fakecouch reset')
        self.view_mock = {}
        self.mock_docs = {}

    def add_view(self, name, view_results):
        self.view_mock[name] = dict([(self._param_key(params), result) for params, result in view_results])
        logger.debug('View added: %s with keys: %s', name, self.view_mock[name].keys())

    def _param_key(self, params):
        params = encode_params(params)
        return urlencode(sorted(params.items(), key=lambda p: p[0]))

    def view(self, view_name, schema=None, wrapper=None, **params):
        view = self.view_mock.get(view_name, {})
        key = self._param_key(params)
        rows = view.get(key, [])
        logger.debug('view(view_name=%s, key=%s): results=%s', view_name, key, rows)
        if wrapper:
            rows = [wrapper(r) for r in rows]
        return MockResult(rows)

    def save_doc(self, doc, **params):
        if '_id' in doc:
            self.mock_docs[doc["_id"]] = doc
            logger.debug('save_doc(%s)', doc['_id'])
        else:
            id = uuid.uuid1()
            doc.update({ '_id': id})
            self.mock_docs[doc["_id"]] = doc
            logger.debug('save_doc(%s): ID generated', doc['_id'])

    def get(self, docid, rev=None, wrapper=None):
        doc = self.mock_docs.get(docid, None)
        logger.debug('get(%s): %s', docid, 'Found' if doc else 'Not found')
        if not doc:
            raise ResourceNotFound
        elif wrapper:
            return wrapper(doc)
        else:
            return doc

    def open_doc(self, docid):
        logger.debug('open_doc(%s)', docid)
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
