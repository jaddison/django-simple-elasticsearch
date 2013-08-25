from django import forms
from django.conf import settings
from django.core.paginator import Paginator, Page, EmptyPage
from django.http import Http404
from django.utils import six
from pyelasticsearch import ElasticSearch


class ESPaginator(Paginator):
    """
    Override Django's built-in Paginator class to take in a count/total number of items;
    ElasticSearch provides the total as a part of the query results, so we can minimize hits.

    Also change `page()` method to use custom ESPage class (see below).
    """
    def __init__(self, *args, **kwargs):
        count = kwargs.pop('count', None)
        super(ESPaginator, self).__init__(*args, **kwargs)
        self._count = count

    def page(self, number):
        "Returns a Page object for the given 1-based page number."
        number = self.validate_number(number)
        return ESPage(self.object_list, number, self)


class ESPage(Page):
    def __getitem__(self, index):
        if not isinstance(index, (slice,) + six.integer_types):
            raise TypeError
        obj = self.object_list[index]
        return obj.get('_source', obj)


class ESSearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        try:
            self.page = int(kwargs.pop('page', 1))
        except (ValueError, TypeError):
            self.page = 1
        try:
            self.page_size = int(kwargs.pop('page_size', 20))
        except (ValueError, TypeError):
            self.page_size = 20

        self.count_only = kwargs.pop('count_only', False)
        self.query_params = kwargs.pop('query_params', {})
        self.es = kwargs.pop('es', None)

        super(ESSearchForm, self).__init__(*args, **kwargs)

    def get_index(self):
        # return the ES index name (or multiple comma-separated) you want to target, or None if you don't want to target an index
        raise NotImplementedError

    def get_type(self):
        # return the ES type name (or multiple comma-separated) you want to target, or None if you don't want to target a type
        raise NotImplementedError

    def prepare_query(self):
        # `count` is a boolean indicating whether we want to simply get
        # the count of matchin docs or the actual results
        raise NotImplementedError

    def search(self):
        responses = ESSearchProcessor(self).search()
        try:
            # there will only be a single response from a ESSearchForm
            response = responses[0]
        except IndexError:
            response = {}

        return response

    def process_response(self, response):
        return ESSearchResponse(response, self.page, self.page_size, self.query_params)



class ESSearchResponse(object):
    # TODO: look to add in some error detection and introspection
    # capabilities to this class; perhaps also hooks to do graphite/
    # logstash timing/error API hits
    def __init__(self, payload, page, page_size, query_params={}):
        self.page = page
        self.page_size = page_size
        self.query_params = query_params

        self.query_stats = payload
        self.hit_stats = self.query_stats.pop('hits', {})
        self.hit_data = self.hit_stats.pop('hits', [])

    def total(self):
        return self.hit_stats.get('total', 0)

    def results(self, paginate=True):
        if paginate:
            paginator = ESPaginator(
                self.hit_data,
                self.page_size,
                count=self.total()
            )
            return paginator.page(self.page)

        return self.hit_data


class ESSearchProcessor(object):
    def __init__(self, forms, es=None):
        if type(forms) not in (list, tuple):
            forms = [forms,]
        self.forms = forms
        self.es = es or ElasticSearch(settings.ES_CONNECTION_URL)

    def search(self):
        msearch_data = u''
        for form in self.forms:
            data = {'index': form.get_index(), 'type': form.get_type()}
            if 'routing' in form.query_params:
                data['routing'] = form.query_params.get('routing')
            if 'search_type' in form.query_params:
                data['search_type'] = form.query_params.get('search_type')

            query = form.prepare_query()
            query['from'] = (form.page - 1) * form.page_size
            query['size'] = form.page_size

            msearch_data += self.es._encode_json(data) + '\n'
            msearch_data += self.es._encode_json(query) + '\n'

        if msearch_data:
            data = self.es.send_request(
                'POST',
                ['_msearch'],
                msearch_data,
                encode_body=False
            )
            responses = []
            if data:
                for i, tmp in enumerate(data.get('responses', [])):
                    responses.append(self.forms[i].process_response(tmp))

            return responses

        return []
