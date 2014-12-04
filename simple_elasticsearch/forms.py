from django import forms
from django.core.paginator import Paginator, Page
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from elasticsearch_dsl.result import Response
from elasticsearch_dsl.utils import AttrDict

from . import settings as es_settings


class DSEPaginator(Paginator):
    """
    Override Django's built-in Paginator class to take in a count/total number of items;
    Elasticsearch provides the total as a part of the query results, so we can minimize hits.
    """
    def __init__(self, *args, **kwargs):
        super(DSEPaginator, self).__init__(*args, **kwargs)
        self._count = self.object_list.hits.total

    def page(self, number):
        # this is overridden to prevent any slicing of the object_list - Elasticsearch has
        # returned the sliced data already.
        number = self.validate_number(number)
        return Page(self.object_list, number, self)


class DSEResponse(Response):
    def __init__(self, d, page=None, page_size=None):
        super(DSEResponse, self).__init__(d)

        # __setattr__ is overridden in parent class; assign these values
        # manually to prevent the new __setattr__ from firing
        super(AttrDict, self).__setattr__('_page_num', page)
        super(AttrDict, self).__setattr__('_page_size', page_size)

    def __len__(self):
        return len(self.hits)

    @property
    def page(self):
        if not hasattr(self, '_page'):
            paginator = DSEPaginator(self, self._page_size)
            # avoid assigning _page into self._d_
            super(AttrDict, self).__setattr__('_page', paginator.page(self._page_num))
        return self._page


class ElasticsearchForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.query_params = kwargs.pop('query_params', {}).copy()
        self.es = kwargs.pop('es', None)

        super(ElasticsearchForm, self).__init__(*args, **kwargs)

    def get_index(self):
        # return the ES index name (or multiple comma-separated) you want to
        # target, or '' if you don't want to target an index
        return ''

    def get_type(self):
        # return the ES type name (or multiple comma-separated) you want to
        # target, or '' if you don't want to target a type
        return ''

    def prepare_query(self):
        raise NotImplementedError

    def search(self, page=1, page_size=20):
        esp = ElasticsearchProcessor(self.es)
        esp.add_search(self, page, page_size)
        responses = esp.search()

        # there will only be a single response from a ElasticsearchForm
        return responses[0]


class ElasticsearchProcessor(object):

    def __init__(self, es=None):
        self.es = es or Elasticsearch(es_settings.ELASTICSEARCH_SERVER)
        self.bulk_search_data = []
        self.page_ranges = []

    def reset(self):
        self.bulk_search_data = []
        self.page_ranges = []

    def add_search(self, query, page=1, page_size=20, index='', doc_type='', query_params={}):
        if isinstance(query, ElasticsearchForm):
            form = query
            index = index or form.get_index()
            doc_type = doc_type or form.get_type()

            qp = form.query_params.copy()
            qp.update(query_params)
            query_params = qp

            query = form.prepare_query()
        elif isinstance(query, Search):
            dsl_search = query
            index = index or dsl_search._index
            doc_type = doc_type or dsl_search._doc_type

            qp = dsl_search._params.copy()
            qp.update(query_params)
            query_params = qp

            query = dsl_search.to_dict()
        elif isinstance(query, dict):
            pass
        else:
            # we don't support any other type of object
            return

        try:
            page = int(page)
        except ValueError:
            page = 1

        try:
            page_size = int(page_size)
        except ValueError:
            page_size = 20

        query['from'] = (page - 1) * page_size
        query['size'] = page_size

        # save these here so we can attach the info the the responses below
        self.page_ranges.append((page, page_size))

        data = query_params.copy()
        if index:
            data['index'] = index
        if doc_type:
            data['type'] = doc_type

        self.bulk_search_data.append(data)
        self.bulk_search_data.append(query)

    def search(self):
        responses = []

        if self.bulk_search_data:
            data = self.es.msearch(self.bulk_search_data)
            if data:
                for i, tmp in enumerate(data.get('responses', [])):
                    responses.append(DSEResponse(tmp, *self.page_ranges[i]))

        self.reset()

        return responses
