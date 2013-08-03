This is an ALPHA level package - it is in flux and if you use it, your project may break with package updates.
----------------

Simple method of creating ElasticSearch indexes for Django projects. Options: auto index/delete with model signals, bulk submit ES operations on request_finished signal, (future) support for RabbitMQ ES 'river' configuration. Management command to handle broad initialization and indexing.

To use the request_finished signal to bulk update ES and ensure that all your management commands work correctly with signals/bulk updating, you will need to update your manage.py script with this snippet:

```python
from simple_elasticsearch.settings import ES_USE_REQUEST_FINISHED_SIGNAL
if ES_USE_REQUEST_FINISHED_SIGNAL:
    from simple_elasticsearch.indexes import process_bulk_data
    process_bulk_data(None)
```

TODO:

  - mention Celery integration custom task in detail (in flux)