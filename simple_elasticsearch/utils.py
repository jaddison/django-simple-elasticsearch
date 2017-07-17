import collections
import datetime
import gc
import sys
from django.conf import settings
from django.http import Http404
from elasticsearch import Elasticsearch, NotFoundError

from simple_elasticsearch.search import Result
from . import settings as es_settings
from .signals import post_indices_create, post_indices_rebuild

try:
    from importlib import import_module
except ImportError:
    from django.utils.importlib import import_module

_elasticsearch_indices = collections.defaultdict(lambda: [])


def get_indices(indices=[]):
    if not _elasticsearch_indices:
        type_classes = getattr(settings, 'ELASTICSEARCH_TYPE_CLASSES', ())
        if not type_classes:
            raise Exception('Missing `ELASTICSEARCH_TYPE_CLASSES` in project `settings`.')

        for type_class in type_classes:
            package_name, klass_name = type_class.rsplit('.', 1)
            try:
                package = import_module(package_name)
                klass = getattr(package, klass_name)
            except ImportError:
                sys.stderr.write('Unable to import `{}`.\n'.format(type_class))
                continue
            _elasticsearch_indices[klass.get_index_name()].append(klass)

    if not indices:
        return _elasticsearch_indices
    else:
        result = {}
        for k, v in _elasticsearch_indices.items():
            if k in indices:
                result[k] = v
        return result


def create_aliases(es=None, indices=[]):
    es = es or Elasticsearch(**es_settings.ELASTICSEARCH_CONNECTION_PARAMS)

    current_aliases = es.indices.get_alias()
    aliases_for_removal = collections.defaultdict(lambda: [])
    for item, tmp in current_aliases.items():
        for iname in list(tmp.get('aliases', {}).keys()):
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
    for index_alias, type_classes in get_indices(indices).items():
        index_settings = es_settings.ELASTICSEARCH_DEFAULT_INDEX_SETTINGS
        index_settings = recursive_dict_update(
            index_settings,
            es_settings.ELASTICSEARCH_CUSTOM_INDEX_SETTINGS.get(index_alias, {})
        )

        index_name = "{0}-{1}".format(index_alias, now)

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

    # `aliases` is a list of (index alias, index timestamped-name) tuples
    post_indices_create.send(None, indices=aliases, aliases_set=set_aliases)

    return result, aliases


def rebuild_indices(es=None, indices=[], set_aliases=True):
    es = es or Elasticsearch(**es_settings.ELASTICSEARCH_CONNECTION_PARAMS)

    created_indices, aliases = create_indices(es, indices, False)

    # kludge to avoid OOM due to Django's query logging
    # db_logger = logging.getLogger('django.db.backends')
    # oldlevel = db_logger.level
    # db_logger.setLevel(logging.ERROR)

    current_index_name = None
    current_index_settings = {}

    def change_index():
        if current_index_name:
            # restore the original (or their ES defaults) settings back into
            # the index to restore desired elasticsearch functionality
            settings = {
                'number_of_replicas': current_index_settings.get('index', {}).get('number_of_replicas', 1),
                'refresh_interval': current_index_settings.get('index', {}).get('refresh_interval', '1s'),
            }
            es.indices.put_settings({'index': settings}, current_index_name)
            es.indices.refresh(current_index_name)

    for type_class, index_alias, index_name in created_indices:
        if index_name != current_index_name:
            change_index()

            # save the current index's settings locally so that we can restore them after
            current_index_settings = es.indices.get_settings(index_name).get(index_name, {}).get('settings', {})
            current_index_name = index_name

            # modify index settings to speed up bulk indexing and then restore them after
            es.indices.put_settings({'index': {
                'number_of_replicas': 0,
                'refresh_interval': '-1',
            }}, index=index_name)

        try:
            type_class.bulk_index(es, index_name)
        except NotImplementedError:
            sys.stderr.write('`bulk_index` not implemented on `{}`.\n'.format(type_class.get_index_name()))
            continue
    else:
        change_index()

    # return to the norm for db query logging
    # db_logger.setLevel(oldlevel)

    if set_aliases:
        create_aliases(es, aliases)
        if es_settings.ELASTICSEARCH_DELETE_OLD_INDEXES:
            delete_indices(es, [a for a, i in aliases])

    # `aliases` is a list of (index alias, index timestamped-name) tuples
    post_indices_rebuild.send(None, indices=aliases, aliases_set=set_aliases)

    return created_indices, aliases


def delete_indices(es=None, indices=[], only_unaliased=True):
    es = es or Elasticsearch(**es_settings.ELASTICSEARCH_CONNECTION_PARAMS)
    indices = indices or get_indices(indices=[]).keys()
    indices_to_remove = []
    for index, aliases in es.indices.get_alias().items():
        # Make sure it isn't currently aliased, which would mean it's active (UNLESS
        # we want to force-delete all `simple_elasticsearch`-managed indices).
        #   AND
        # Make sure it isn't an arbitrary non-`simple_elasticsearch` managed index.
        if (not only_unaliased or not aliases.get('aliases')) and index.split('-', 1)[0] in indices:
            indices_to_remove.append(index)

    if indices_to_remove:
        es.indices.delete(','.join(indices_to_remove))
    return indices_to_remove


def recursive_dict_update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = recursive_dict_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def queryset_iterator(queryset, chunksize=1000, order_by='pk'):
    if order_by:
        queryset = queryset.order_by(order_by)

    chunk = 0
    while True:
        n = 0
        for n, row in enumerate(queryset[chunk * chunksize:(chunk + 1) * chunksize]):
            yield row

        if not n:
            break
        chunk += 1
        gc.collect()


def get_from_es_or_None(index, type, id, **kwargs):
    es = kwargs.pop('es', Elasticsearch(es_settings.ELASTICSEARCH_SERVER))
    try:
        return Result(es.get(index, id, type, **kwargs))
    except NotFoundError:
        return None


def get_from_es_or_404(index, type, id, **kwargs):
    item = get_from_es_or_None(index, type, id, **kwargs)
    if not item:
        raise Http404('No {0} matches the parameters.'.format(type))
    return item
