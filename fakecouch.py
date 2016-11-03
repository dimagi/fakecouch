import uuid
import logging

# this import pattern lets fakecouch not depend on couchdbkit
try:
    import couchdbkit
except ImportError:
    import json

    class ResourceNotFound(Exception):
        pass

    class ResourceConflict(Exception):
        pass


    class BulkSaveError(Exception):
        def __init__(self, errors, results, *args):
            self.errors = errors
            self.results = results

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
    from couchdbkit.exceptions import ResourceNotFound, ResourceConflict, BulkSaveError
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
                (resource, self._transform_view_results(view_results))
                for resource, view_results in views.items()])
        else:
            self.view_mock = {}

        if isinstance(docs, list):
            self.mock_docs = {
                doc['_id']: doc for doc in docs
            }
        else:
            self.mock_docs = docs or {}

    def reset(self):
        logger.info('Fakecouch reset')
        self.view_mock = {}
        self.mock_docs = {}

    def add_view(self, name, view_results):
        """Add a view and results to the mock.

        :param view_results: A list of tuples where the first element is a dictionary
        of view query parameters and the second element is a list of view result rows.
        """
        self.view_mock[name] = self._transform_view_results(view_results)
        logger.debug('View added: %s with keys: %s', name, self.view_mock[name].keys())

    def update_view(self, name, view_results):
        """Update the view results for a given view.

        :param view_results: A list of tuples where the first element is a dictionary
        of view query parameters and the second element is a list of view result rows.
        :raises KeyError: If the DB does not already have a view with the given name
        """
        self.view_mock[name].update(self._transform_view_results(view_results))

    def remove_view(self, name):
        try:
            del self.view_mock[name]
        except KeyError:
            pass

    def _transform_view_results(self, view_results):
        return {self._param_key(params): result for params, result in view_results}

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
            self._check_conflict(doc)
            doc["_rev"] = _next_rev(doc.get("_rev"))
            self.mock_docs[doc["_id"]] = doc
            logger.debug('save_doc(%s)', doc['_id'])
        else:
            id = str(uuid.uuid1())
            rev = _next_rev()
            doc.update({ '_id': id, '_rev': rev})
            self.mock_docs[doc["_id"]] = doc
            logger.debug('save_doc(%s): ID generated', doc['_id'])

    def _check_conflict(self, doc):
        existing = self.mock_docs.get(doc['_id'])
        if existing and existing.get('_rev') != doc.get('_rev'):
            raise ResourceConflict()

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

    def save_docs(self, docs, use_uuids=True, all_or_nothing=False, new_edits=None, **params):
        if new_edits or new_edits is None:
            errors = []
            error_ids = set()
            for doc in docs:
                try:
                    self._check_conflict(doc)
                except ResourceConflict:
                    error_ids.add(doc['_id'])
                    errors.append({
                        'error': 'conflict', 'id': doc['_id']
                    })

            if all_or_nothing and errors:
                raise BulkSaveError(errors, [])
            else:
                results = []
                for doc in docs:
                    if doc['_id'] not in error_ids:
                        self.save_doc(doc)
                        results.append({'id': doc['_id'], '_rev': doc['_rev']})

                if errors:
                    raise BulkSaveError(errors, results)

            return results
        else:
            # with ``new_edits=False`` only save the doc if it's rev
            # is greater than the existing doc's rev.
            for doc in docs:
                existing = self.mock_docs.get(doc['_id'])
                if existing:
                    existing_rev_num = _get_rev_num(existing.get('_rev'))
                    new_rev_num = _get_rev_num(doc.get('_rev'))
                    if new_rev_num > existing_rev_num:
                        self.mock_docs[doc['_id']] = doc
                else:
                    if '_rev' not in doc:
                        doc["_rev"] = _next_rev()
                    self.mock_docs[doc['_id']] = doc

            return []

    bulk_save = save_docs


def _next_rev(current_rev=None):
    rev_num = _get_rev_num(current_rev)
    if not rev_num or rev_num == -1:
        rev_num = 0
    return '{}-{}'.format(rev_num + 1, str(uuid.uuid1()))


def _get_rev_num(rev=None):
    if not rev:
        return None

    try:
        return int(rev.split('-')[0])
    except ValueError:
        return -1


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
