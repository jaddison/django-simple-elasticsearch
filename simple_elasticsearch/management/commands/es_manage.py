import datetime
import sys
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
            self.subcommand_list()
        elif options.get('initialize'):
            self.subcommand_initialize(requested_indexes, no_input)
        elif options.get('delete'):
            self.subcommand_delete(requested_indexes, no_input)
        elif options.get('rebuild'):
            self.subcommand_rebuild(requested_indexes, no_input)

    def get_existing_aliases(self, indexes=None):
        existing_aliases = {}
        try:
            tmp = self.es.aliases(index=indexes, es_ignore_indices='missing')
        except ElasticHttpNotFoundError:
            return existing_aliases

        for k,v in tmp.iteritems():
            existing_aliases[k] = v.get('aliases', {}).keys()

        return existing_aliases

    def update_aliases(self, new_aliases):
        old_aliases = self.get_existing_aliases(new_aliases.keys())
        updates = [{"remove": {"index": index, 'alias': alias}} for index, aliases in old_aliases.iteritems() for alias in aliases]
        updates += [{"add": {"index": index, 'alias': alias}} for alias, index in new_aliases.iteritems()]
        self.es.update_aliases({
            'actions': updates
        })

    def create_index(self, index_alias):
        # Combine the configured default index settings with the 'index'-specific
        # settings defined in the project's settings.py
        index_settings = es_settings.ES_DEFAULT_INDEX_SETTINGS
        index_settings = recursive_dict_update(index_settings, es_settings.ES_CUSTOM_INDEX_SETTINGS.get(index_alias, {}))

        # Get any defined type mappings from our ESBaseIndex-derived class, if any. (defaults to letting ES
        # auto-create the mapping based on data input at index time)
        type_mappings = {}
        for obj in self.all_indexes[index_alias]:
            tmp = obj.get_mapping()
            if tmp:
                type_mappings[obj.get_type_name()] = tmp

        # if we got any type mappings, put them in the index settings
        if type_mappings:
            index_settings['mappings'] = type_mappings

        index_name = u"{0}-{1}".format(index_alias, datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        self.es.create_index(index_name, index_settings)
        return index_name

    def subcommand_list(self):
        print u"Available ES indexes:"
        for index, values in self.all_indexes.iteritems():
            print u" - index '{0}' contains these types:".format(index)
            for value in values:
                print u"  - type '{0}' which indexes the '{1}' model through '{2}'".format(value.get_type_name(), value.get_model().__name__, value.__class__.__name__)

    def subcommand_initialize(self, indexes=None, no_input=False):
        if no_input or 'yes' == raw_input(u'Are you sure you want to initialize {0} index(es)? [yes/NO]: '.format(u'the ' + u', '.join(indexes) if indexes else '**ALL**')).lower():
            new_aliases = {}
            # process everything for creating each index
            for index_name in (indexes or self.all_index_names):
                new_aliases[index_name] = self.create_index(index_name)

            self.update_aliases(new_aliases)
            print 'Creating indexes... complete.'

    def subcommand_delete(self, indexes=None, no_input=False):
        if no_input or 'yes' == raw_input(u'Are you sure you want to delete {0} index(es)? [yes/NO]: '.format(u'the ' + u', '.join(indexes) if indexes else '**ALL simple_elasticsearch managed**')).lower():
            try:
                self.es.delete_index(indexes or self.all_index_names)
            except ElasticHttpNotFoundError:
                pass
            print 'Deleting indexes... complete.'

    def subcommand_rebuild(self, indexes, no_input=False):
        if no_input or 'yes' == raw_input(u'Are you sure you want to reindex {0} index(es)? [yes/NO]: '.format(u'the ' + u', '.join(indexes) if indexes else '**ALL**')).lower():
            old_aliases = self.get_existing_aliases(indexes)

            # process everything for creating each index
            for index_alias in (indexes or self.all_index_names):
                # create a new timestamp-named index
                index_name = self.create_index(index_alias)

                print "Starting rebuild of '{0}' (aliased to real index '{1}'):".format(index_alias, index_name)
                for index_type in self.all_indexes[index_alias]:
                    print " - processing type '{0}'... ".format(index_type.get_type_name()),
                    sys.stdout.flush()
                    self.es.send_request(
                        'PUT',
                        [index_name, '_settings'],
                        self.es._encode_json({'index': {'refresh_interval': '-1', "merge.policy.merge_factor": 30}}),
                        encode_body=False
                    )

                    i = 0
                    qs = index_type.get_queryset()
                    for i, item in enumerate(queryset_iterator(qs)):
                        index_type.perform_action(item, 'index', index_name=index_name)

                    self.es.send_request(
                        'PUT',
                        [index_name, '_settings'],
                        self.es._encode_json({'index': {'refresh_interval': '1s', "merge.policy.merge_factor": 10}}),
                        encode_body=False
                    )
                    print "complete. ({0} items)".format(i+1)

                # tell ES to 'flip the switch' to merge segments and make the data available for searching
                self.es.refresh(index_name)

                # remove the old aliases for this index and add the new one; an atomic operation that prevents people from seeing downtime
                self.update_aliases({index_alias:index_name})
                print " - refresh and aliasing updates complete."

            if old_aliases.keys() and raw_input("Delete old unaliased indexes ({0})? (y/n): ".format(u', '.join(old_aliases.keys()))).lower() == 'y':
                self.es.delete_index(old_aliases.keys())
                print 'Deleted old aliased indexes: ', u', '.join(old_aliases.keys())
