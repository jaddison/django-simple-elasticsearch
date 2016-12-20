from django.core.paginator import Paginator as DjangoPaginator
from django.utils.functional import cached_property
from elasticsearch import Elasticsearch

from . import settings as es_settings


class Paginator(DjangoPaginator):
    def __init__(self, response, *args, **kwargs):
        # `response.results` is a generator, however `Paginator` was changed in 1.10
        # to require an object with either a `.count()` method (ie. QuerySet) or able
        # to call `len()` on the object - forcing the generator to resolve to a list
        # for this reason.
        super(Paginator, self).__init__(list(response.results), *args, **kwargs)

        # Override to set the count/total number of items; Elasticsearch provides the total
        # as a part of the query results, so we can minimize hits.
        self._count = response.total

    def page(self, number):
        # this is overridden to prevent any slicing of the object_list - Elasticsearch has
        # returned the sliced data already.
        number = self.validate_number(number)
        return self._get_page(self.object_list, number, self)

    @property
    def count(self):
        return self._count


class Response(object):
    def __init__(self, d, page_num, page_size):
        self._page_num = page_num
        self._page_size = page_size

        self.response_meta = d
        self.results_meta = d.pop('hits', {})
        self._results = self.results_meta.pop('hits', [])
        self.aggregations = self.response_meta.pop('aggregations', {})

    def __len__(self):
        return len(self._results)

    @property
    def total(self):
        return self.results_meta.get('total', 0)

    @property
    def results(self):
        for item in self._results:
            yield Result(item)

    @property
    def max_score(self):
        return self.results_meta.get('max_score', 0)

    @cached_property
    def page(self):
        paginator = Paginator(self, self._page_size)
        return paginator.page(self._page_num)


class Result(object):
    def __init__(self, data):
        self.result_meta = data
        self.data = self.result_meta.pop('_source', {})


class SimpleSearch(object):
    def __init__(self, es=None):
        self.es = es or Elasticsearch(es_settings.ELASTICSEARCH_SERVER)
        self.bulk_search_data = []
        self.page_ranges = []

    def reset(self):
        self.bulk_search_data = []
        self.page_ranges = []

    def add_search(self, query, page=1, page_size=20, index='', doc_type='', query_params=None):
        query_params = query_params if query_params is not None else {}

        page = int(page)
        page_size = int(page_size)

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
            for i, tmp in enumerate((data or {}).get('responses', [])):
                responses.append(Response(tmp, *self.page_ranges[i]))

        self.reset()

        return responses
