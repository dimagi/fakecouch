import uuid
import logging

# this import pattern lets fakecouch not depend on couchdbkit
from couchdbkit.exceptions import ResourceConflict

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


    class ViewResults(object):
        def __init__(self, fetch, arg, wrapper, schema, params):
            assert not (wrapper and schema)
            self.wrapper = wrapper or schema or (lambda row: row)
            self.json_body = fetch(arg, params).json_body

        def all(self):
            return [self.wrapper(row) for row in self.json_body['rows']]

        @property
        def total_rows(self):
            return len(self.json_body['rows'])

        def __iter__(self):
            return iter(self.all())

else:
    from couchdbkit import ResourceNotFound
    from couchdbkit.resource import encode_params
    from couchdbkit.client import ViewResults


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
                    {'id': '123', 'key': 'abc', 'value': None, 'doc': {...},
                    ... view result rows ...
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

    def raw_view(self, view_name, params):
        view = self.view_mock.get(view_name, {})
        key = self._param_key(params)

        if key not in view and 'wrap_doc' in params:
            params.pop('wrap_doc')
            key = self._param_key(params)

        result = view.get(key, [])
        logger.debug('view(view_name=%s, key=%s): result=%s', view_name, key, result)
        return JsonResponse(result)

    def view(self, view_name, schema=None, wrapper=None, **params):
        return ViewResults(self.raw_view, view_name, wrapper, schema, params)

    def save_doc(self, doc, **params):
        if '_id' in doc:
            existing = self.mock_docs.get(doc['_id'])
            if existing and existing.get('_rev') != doc.get('_rev'):
                raise ResourceConflict()
            doc["_rev"] = str(uuid.uuid1())
            self.mock_docs[doc["_id"]] = doc
            logger.debug('save_doc(%s)', doc['_id'])
        else:
            id = str(uuid.uuid1())
            rev = str(uuid.uuid1())
            doc.update({ '_id': id, '_rev': rev})
            self.mock_docs[doc["_id"]] = doc
            logger.debug('save_doc(%s): ID generated', doc['_id'])

    def get(self, docid, rev=None, wrapper=None):
        doc = self.mock_docs.get(docid, None)
        logger.debug('get(%s): %s', docid, 'Found' if doc else 'Not found')
        if not doc:
            raise ResourceNotFound()
        elif wrapper:
            return wrapper(doc)
        else:
            return doc

    def open_doc(self, docid):
        logger.debug('open_doc(%s)', docid)
        doc = self.mock_docs.get(docid, None)
        return doc

    def delete_doc(self, docid):
        if docid not in self.mock_docs:
            raise ResourceNotFound()
        else:
            del self.mock_docs[docid]


class JsonResponse(object):
    def __init__(self, json_body_or_rows):
        def fake_row(row):
            if not isinstance(row, dict):
                raise Exception('Rows must be dicts')

            return {
                'id': row.get('id', row.get('_id', None)),
                'key': row.get('key', None),
                'value': row.get('value', None),
                'doc': row.get('doc', row if '_id' in row else None)
            }

        if isinstance(json_body_or_rows, dict):
            self.json_body = json_body_or_rows
        elif isinstance(json_body_or_rows, list):
            self.json_body = {
                'rows': [fake_row(row) for row in json_body_or_rows],
                'total_rows': len(json_body_or_rows),
            }
