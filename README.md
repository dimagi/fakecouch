# fakecouch [![Build Status](https://travis-ci.org/dimagi/fakecouch.png)](https://travis-ci.org/dimagi/fakecouch)

Fake implementation of CouchDBKit api for testing purposes.

## Usage

Monkey patch fack db into CouchDBKit
```python
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
        },
        docs={
            '123': { ... doc dict ... }
        })

DocumentSchema._db = fakedb
DocumentBase._db = fakedb
```

See tests for further useage.
