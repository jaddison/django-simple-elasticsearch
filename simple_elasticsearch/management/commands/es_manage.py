from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from pyelasticsearch import ElasticSearch, ElasticHttpNotFoundError

from ...utils import queryset_iterator, recursive_dict_update, get_all_indexes
from ... import settings as es_settings


class ESCommandError(CommandError):
    pass

class Command(BaseCommand):
    help = ''
    option_list = BaseCommand.option_list + (
        make_option(
            '--indexes',
            action='store',
            dest='indexes',
            default='',
        ),
        make_option(
            '--list',
            action='store_true',
            dest='list',
            default=False,
        ),
        make_option(
            '--no_input',
            action='store_true',
            dest='no_input',
            default=False,
        ),
        make_option(
            '--refresh',
            action='store_true',
            dest='refresh',
            default=False,
        ),
        make_option(
            '--delete',
            action='store_true',
            dest='delete',
            default=False,
        ),
        make_option(
            '--initialize',
            action='store_true',
            dest='initialize',
            default=False,
        ),
        make_option(
            '--rebuild',
            action='store_true',
            dest='rebuild',
            default=False,
        ),
        make_option(
            '--update',
            action='store_true',
            dest='update',
            default=False,
        )
    )
    es = ElasticSearch(es_settings.ES_CONNECTION_URL)

    def handle(self, *args, **options):
        no_input = options.get('no_input')
        # get all available *active* (meaning, in INSTALLED_APPS) ESBaseIndex-derived classes in the project
        self.all_indexes = get_all_indexes(es=self.es)
        # get a copy of the available ES indexes from the active classes
        self.all_index_names = self.all_indexes.keys()

        requested_indexes = None
        if options.get('indexes'):
            requested_indexes = options.get('indexes', '').split(',')
            for index in requested_indexes:
                if index not in self.all_index_names:
                    raise ESCommandError(u"Index '{0}' is not associated with any models through ESBaseIndex-derived classes.".format(index))

        if options.get('list'):
            self.list()
        elif options.get('refresh'):
            self.refresh(requested_indexes, no_input)
        elif options.get('update'):
            self.update(requested_indexes, no_input)
        elif options.get('delete'):
            self.delete(requested_indexes, no_input)
        elif options.get('rebuild'):
            self.rebuild(requested_indexes, no_input)
        elif options.get('initialize'):
            self.initialize(requested_indexes, no_input)

    def list(self):
        print u"Available ES indexes:"
        for index, values in self.all_indexes.iteritems():
            print u" - index '{0}' contains these types:".format(index)
            for value in values:
                print u"  - type '{0}' which indexes the '{1}' model through '{2}'".format(value.get_type_name(), value.get_model().__name__, value.__class__.__name__)

    def refresh(self, indexes=None, no_input=False):
        if no_input or 'yes' == raw_input(u'Are you sure you want to refresh {0} index(es)? [yes/NO]: '.format(u'the ' + u', '.join(indexes) if indexes else '**ALL**')).lower():
            print 'Refreshing...',
            self.es.refresh(indexes)
            print 'complete.'

    def delete(self, indexes=None, no_input=False):
        if no_input or 'yes' == raw_input(u'Are you sure you want to delete {0} index(es)? [yes/NO]: '.format(u'the ' + u', '.join(indexes) if indexes else '**ALL simple_elasticsearch managed**')).lower():
            print 'Deleting indexes...',
            try:
                self.es.delete_index(indexes or self.all_index_names)
            except ElasticHttpNotFoundError:
                pass
            print 'complete.'

    def initialize(self, indexes=None, no_input=False):
        if no_input or 'yes' == raw_input(u'Are you sure you want to initialize {0} index(es)? [yes/NO]: '.format(u'the ' + u', '.join(indexes) if indexes else '**ALL**')).lower():
            print 'Creating indexes...',
            # process everything for creating each index
            for index in (indexes or self.all_index_names):
                # Combine the configured default index settings with the 'index'-specific
                # settings defined in the project's settings.py
                index_settings = es_settings.ES_DEFAULT_INDEX_SETTINGS
                index_settings = recursive_dict_update(index_settings, es_settings.ES_CUSTOM_INDEX_SETTINGS.get(index, {}))

                # Get any defined type mappings from our ESBaseIndex-derived class, if any. (defaults to letting ES
                # auto-create the mapping based on data input at index time)
                type_mappings = {}
                for obj in self.all_indexes[index]:
                    tmp = obj.get_mapping()
                    if tmp:
                        type_mappings[obj.get_type_name()] = tmp

                # if we got any type mappings, put them in the index settings
                if type_mappings:
                    index_settings['mappings'] = type_mappings

                self.es.create_index(index, index_settings)

            print 'complete.'

    def update(self, indexes, no_input=False):
        if no_input or 'yes' == raw_input(u'Are you sure you want to update {0} index(es)? [yes/NO]: '.format(u'the ' + u', '.join(indexes) if indexes else '**ALL**')).lower():
            # process everything for creating each index
            for index_name in (indexes or self.all_index_names):
                for index in self.all_indexes[index_name]:
                    self.es.send_request(
                        'PUT',
                        [index_name, '_settings'],
                        self.es._encode_json({'index': {'refresh_interval': '-1', "merge.policy.merge_factor" : 30}}),
                        encode_body=False
                    )

                    i = 0
                    qs = index.get_queryset()
                    for i, item in enumerate(queryset_iterator(qs)):
                        index.perform_action(item, 'index')

                    self.es.send_request(
                        'PUT',
                        [index_name, '_settings'],
                        self.es._encode_json({'index': {'refresh_interval': '1s', "merge.policy.merge_factor" : 10}}),
                        encode_body=False
                    )
                    print "Updated index '{0}', type '{1}' ({2} items).".format(index_name, index.get_type_name(), i+1)

    def rebuild(self, indexes=None, no_input=False):
        # TODO: use aliases in here to prevent downtime; create new indexes with unique names,
        # update all documents into them, and then change the aliases to the new indexes and
        # delete the old indexes.
        if no_input or 'yes' == raw_input(u'Are you sure you want to delete and rebuild {0} index(es)? [yes/NO]: '.format(u'the ' + u', '.join(indexes) if indexes else '**ALL**')).lower():
            self.delete(indexes, no_input=True)
            self.initialize(indexes, no_input=True)
            self.update(indexes, no_input=True)
            self.refresh(indexes, no_input=True)
