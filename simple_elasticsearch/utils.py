import collections
import gc
import inspect

from django.conf import settings
from django.http import Http404
from django.utils.importlib import import_module
from pyelasticsearch import ElasticSearch, ElasticHttpNotFoundError

try:
    import celery
except ImportError:
    celery = None

from .indexes import ESBaseIndex


all_indexes = None


def get_all_indexes(es=None):
    global all_indexes
    if not all_indexes:
        all_indexes = collections.defaultdict(lambda: [])
        for app in settings.INSTALLED_APPS:
            try:
                index_module = import_module('.es', app)
            except ImportError:
                continue

            for name, item in inspect.getmembers(index_module):
                if inspect.isclass(item) and issubclass(item, ESBaseIndex) and item is not ESBaseIndex:
                    obj = item(es=es)
                    all_indexes[obj.get_index_name()].append(obj)

    return all_indexes


def recursive_dict_update(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = recursive_dict_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def queryset_iterator(queryset, chunksize=1000):
    last_pk = queryset.order_by('-pk')[0].pk
    queryset = queryset.order_by('pk')
    pk = queryset[0].pk - 1
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            yield row
        gc.collect()


if celery:
    class ESCallbackTask(celery.Task):
        def _update_es(self):
            try:
                from .indexes import process_bulk_data
            except ImportError:
                # ES_USE_REQUEST_FINISHED_SIGNAL is not enabled, so nothing to do!
                return

            # trigger the sending of bulk data to the elasticsearch `bulk` API endpoint
            process_bulk_data(None)

        def on_success(self, retval, task_id, args, kwargs):
            self._update_es()

        def on_failure(self, exc, task_id, args, kwargs, einfo):
            self._update_es()


def get_from_es_or_None(index, type, id, **kwargs):
    es = kwargs.pop('es', ElasticSearch(settings.ES_CONNECTION_URL))
    try:
        return es.get(index, type, id, **kwargs)
    except ElasticHttpNotFoundError:
        return None


def get_from_es_or_404(index, type, id, **kwargs):
    item = get_from_es_or_None(index, type, id, **kwargs)
    if not item:
        raise Http404('No {0} matches the parameters.'.format(type))
    return item
