from elasticsearch import Elasticsearch, TransportError

from . import settings as es_settings
from .exceptions import MissingObjectError
from .utils import queryset_iterator


class ElasticsearchTypeMixin(object):

    @classmethod
    def get_es(cls):
        if not hasattr(cls, '_es'):
            cls._es = Elasticsearch(**cls.get_es_connection_settings())
        return cls._es

    @classmethod
    def get_es_connection_settings(cls):
        return es_settings.ELASTICSEARCH_CONNECTION_PARAMS

    @classmethod
    def get_index_name(cls):
        raise NotImplementedError

    @classmethod
    def get_type_name(cls):
        raise NotImplementedError

    @classmethod
    def get_document(cls, obj):
        raise NotImplementedError

    @classmethod
    def get_document_id(cls, obj):
        if not obj:
            raise MissingObjectError
        return obj.pk

    @classmethod
    def get_request_params(cls, obj):
        return {}

    @classmethod
    def get_type_mapping(cls):
        return {}

    @classmethod
    def get_queryset(cls):
        raise NotImplementedError

    @classmethod
    def get_bulk_index_limit(cls):
        return 100

    @classmethod
    def get_query_limit(cls):
        return 100

    @classmethod
    def should_index(cls, obj):
        return True

    @classmethod
    def bulk_index(cls, es=None, index_name='', queryset=None):
        es = es or cls.get_es()

        tmp = []

        if queryset is None:
            queryset = cls.get_queryset()

        bulk_limit = cls.get_bulk_index_limit()

        # this requires that `get_queryset` is implemented
        for i, obj in enumerate(queryset_iterator(queryset, cls.get_query_limit())):
            delete = not cls.should_index(obj)

            doc = {}
            if not delete:
                # allow for the case where a document cannot be indexed;
                # the implementation of `get_document()` should return a
                # falsy value.
                doc = cls.get_document(obj)
                if not doc:
                    continue

            data = {
                '_index': index_name or cls.get_index_name(),
                '_type': cls.get_type_name(),
                '_id': cls.get_document_id(obj)
            }
            data.update(cls.get_request_params(obj))
            data = {'delete' if delete else 'index': data}

            # bulk operation instructions/details
            tmp.append(data)

            # only append bulk operation data if it's not a delete operation
            if not delete:
                tmp.append(doc)

            if not i % bulk_limit:
                es.bulk(tmp)
                tmp = []

        if tmp:
            es.bulk(tmp)

    @classmethod
    def index_add(cls, obj, index_name=''):
        if obj and cls.should_index(obj):
            doc = cls.get_document(obj)
            if not doc:
                return False

            cls.get_es().index(
                index_name or cls.get_index_name(),
                cls.get_type_name(),
                doc,
                cls.get_document_id(obj),
                **cls.get_request_params(obj)
            )
            return True
        return False

    @classmethod
    def index_delete(cls, obj, index_name=''):
        if obj:
            try:
                cls.get_es().delete(
                    index_name or cls.get_index_name(),
                    cls.get_type_name(),
                    cls.get_document_id(obj),
                    **cls.get_request_params(obj)
                )
            except TransportError as e:
                if e.status_code != 404:
                    raise
            return True
        return False

    @classmethod
    def index_add_or_delete(cls, obj, index_name=''):
        if obj:
            if cls.should_index(obj):
                return cls.index_add(obj, index_name)
            else:
                return cls.index_delete(obj, index_name)
        return False

    @classmethod
    def save_handler(cls, sender, instance, **kwargs):
        cls.index_add_or_delete(instance)

    @classmethod
    def delete_handler(cls, sender, instance, **kwargs):
        cls.index_delete(instance)
