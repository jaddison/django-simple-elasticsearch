import collections
import gc
import inspect

from django.conf import settings
from django.utils.importlib import import_module

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


def queryset_generator(queryset, chunksize=1000):
    last_pk = queryset.order_by('-pk')[0].pk
    queryset = queryset.order_by('pk')
    pk = queryset[0].pk - 1
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            yield row
        gc.collect()

# def queryset_iterator(queryset, chunksize=1000, reverse=False):
#     ordering = '-' if reverse else ''
#     queryset = queryset.order_by(ordering + 'pk')
#     last_pk = None
#     new_items = True
#     while new_items:
#         new_items = False
#         chunk = queryset
#         if last_pk is not None:
#             func = 'lt' if reverse else 'gt'
#             chunk = chunk.filter(**{'pk__' + func: last_pk})
#         chunk = chunk[:chunksize]
#         row = None
#         for row in chunk:
#             yield row
#         if row is not None:
#             last_pk = row.pk
#             new_items = True

