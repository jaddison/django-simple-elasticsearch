from django import forms
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from elasticsearch_dsl.result import Response

from . import settings as es_settings


class ESSearchForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.query_params = kwargs.pop('query_params', {}).copy()
        self.es = kwargs.pop('es', None)

        super(ESSearchForm, self).__init__(*args, **kwargs)

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
        esp = ESSearchProcessor(self.es)
        esp.add_search(self, page, page_size)
        responses = esp.search()

        # there will only be a single response from a ESSearchForm
        return responses[0]


class ESSearchProcessor(object):

    def __init__(self, es=None):
        self.es = es or Elasticsearch(es_settings.ELASTICSEARCH_SERVER)
        self.bulk_search_data = []
        self.page_ranges = []

    def reset(self):
        self.bulk_search_data = []
        self.page_ranges = []

    def add_search(self, query, page=1, page_size=20, index='', doc_type='', query_params={}):
        if isinstance(query, ESSearchForm):
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
                    response = Response(tmp)

                    # hack the from & size values into response.hits so the user
                    # can do some (fake) Django pagination if desired
                    hits = response.get('hits', {})
                    hits['from'], hits['size'] = self.page_ranges[i]

                    responses.append(response)

        self.reset()

        return responses
