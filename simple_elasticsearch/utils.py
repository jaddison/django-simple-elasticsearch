import collections
import datetime
import gc
import sys

from django.conf import settings
from django.http import Http404
from django.utils.importlib import import_module
from elasticsearch import Elasticsearch, ElasticsearchException

from . import settings as es_settings

try:
    import celery
except ImportError:
    celery = None

from . import settings as es_settings


_elasticsearch_indices = collections.defaultdict(lambda: [])
def get_indices(indices=[]):
    if not _elasticsearch_indices:
        type_classes = getattr(settings, 'ELASTICSEARCH_TYPE_CLASSES', ())
        if not type_classes:
            raise Exception(u'Missing `ELASTICSEARCH_TYPE_CLASSES` in project `settings`.')

        for type_class in type_classes:
            package_name, klass_name = type_class.rsplit('.', 1)
            try:
                package = import_module(package_name)
                klass = getattr(package, klass_name)
            except ImportError:
                sys.stderr.write(u'Unable to import `{}`.\n'.format(type_class))
                continue
            _elasticsearch_indices[klass.get_index_name()].append(klass)

    if not indices:
        return _elasticsearch_indices
    else:
        result = {}
        for k, v in _elasticsearch_indices.iteritems():
            if k in indices:
                result[k] = v
        return result


def create_aliases(es=None, indices=[]):
    es = es or Elasticsearch(**es_settings.ELASTICSEARCH_CONNECTION_PARAMS)

    current_aliases = es.indices.get_aliases()
    aliases_for_removal = collections.defaultdict(lambda: [])
    for item, tmp in current_aliases.iteritems():
        for iname in tmp.get('aliases', {}).keys():
            aliases_for_removal[iname].append(item)

    actions = []
    for index_alias, index_name in indices:
        for item in aliases_for_removal[index_alias]:
            actions.append({
                'remove': {
                    'index': item,
                    'alias': index_alias
                }
            })
        actions.append({
            'add': {
                'index': index_name,
                'alias': index_alias
            }
        })

    es.indices.update_aliases({'actions': actions})


def create_indices(es=None, indices=[], set_aliases=True):
    es = es or Elasticsearch(**es_settings.ELASTICSEARCH_CONNECTION_PARAMS)

    result = []

    aliases = []
    now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    for index_alias, type_classes in get_indices(indices).iteritems():
        index_settings = es_settings.ELASTICSEARCH_DEFAULT_INDEX_SETTINGS
        index_settings = recursive_dict_update(
            index_settings,
            es_settings.ELASTICSEARCH_CUSTOM_INDEX_SETTINGS.get(index_alias, {})
        )

        index_name = u"{0}-{1}".format(index_alias, now)

        aliases.append((index_alias, index_name))

        type_mappings = {}
        for type_class in type_classes:
            tmp = type_class.get_type_mapping()
            if tmp:
                type_mappings[type_class.get_type_name()] = tmp

            result.append((
                type_class,
                index_alias,
                index_name
            ))

        # if we got any type mappings, put them in the index settings
        if type_mappings:
            index_settings['mappings'] = type_mappings

        es.indices.create(index_name, index_settings)

    if set_aliases:
        create_aliases(es, aliases)

    return result, aliases


def rebuild_indices(es=None, indices=[], set_aliases=True):
    es = es or Elasticsearch(**es_settings.ELASTICSEARCH_CONNECTION_PARAMS)

    created_indices, aliases = create_indices(es, indices, False)

    # kludge to avoid OOM due to Django's query logging
    # db_logger = logging.getLogger('django.db.backends')
    # oldlevel = db_logger.level
    # db_logger.setLevel(logging.ERROR)

    for type_class, index_alias, index_name in created_indices:
        try:
            type_class.bulk_index(es, index_name)
        except NotImplementedError:
            sys.stderr.write(u'`bulk_index` not implemented on `{}`.\n'.format(type_class.get_index_name()))
            continue

    # return to the norm for db query logging
    # db_logger.setLevel(oldlevel)

    if set_aliases:
        create_aliases(es, aliases)

    return created_indices, aliases


def recursive_dict_update(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = recursive_dict_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def queryset_iterator(queryset, chunksize=1000):
    try:
        last_pk = queryset.order_by('-pk')[0].pk
    except IndexError:
        return

    queryset = queryset.order_by('pk')
    pk = queryset[0].pk - 1
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            yield row
        gc.collect()


def get_from_es_or_None(index, type, id, **kwargs):
    es = kwargs.pop('es', Elasticsearch(es_settings.ELASTICSEARCH_SERVER))
    try:
        return es.get(index, id, type, **kwargs)
    except ElasticsearchException:
        return None


def get_from_es_or_404(index, type, id, **kwargs):
    item = get_from_es_or_None(index, type, id, **kwargs)
    if not item:
        raise Http404('No {0} matches the parameters.'.format(type))
    return item
