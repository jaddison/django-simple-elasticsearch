import sys
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from ...utils import get_indices, create_indices, rebuild_indices


class ESCommandError(CommandError):
    pass

class Command(BaseCommand):
    help = ''
    option_list = BaseCommand.option_list + (
        make_option(
            '--list',
            action='store_true',
            dest='list',
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
            '--no_input',
            action='store_true',
            dest='no_input',
            default=False,
        ),
        make_option(
            '--indexes',
            action='store',
            dest='indexes',
            default='',
        )
    )

    def handle(self, *args, **options):
        no_input = options.get('no_input')

        requested_indexes = options.get('indexes', '') or []
        if requested_indexes:
            requested_indexes = requested_indexes.split(',')

        if options.get('list'):
            self.subcommand_list()
        elif options.get('initialize'):
            self.subcommand_initialize(requested_indexes, no_input)
        elif options.get('rebuild'):
            self.subcommand_rebuild(requested_indexes, no_input)

    def subcommand_list(self):
        print u"Available ES indexes:"
        for index_name, type_classes in get_indices().iteritems():
            print u" - index '{0}':".format(index_name)
            for type_class in type_classes:
                print u"  - type '{0}'".format(type_class.get_type_name())

    def subcommand_initialize(self, indexes=None, no_input=False):
        input = 'y' if no_input else ''
        while input != 'y':
            input = raw_input(u'Are you sure you want to initialize {0} index(es)? [y/N]: '.format(u'the ' + u', '.join(indexes) if indexes else '**ALL**')).lower()
            if input == 'n':
                break

        if input == 'y':
            sys.stdout.write(u"Creating ES indexes: ")
            results, aliases = create_indices(indexes)
            sys.stdout.write(u"complete.\n")
            for alias, index in aliases:
                print u"'{0}' aliased to '{1}'".format(alias, index)

    def subcommand_rebuild(self, indexes, no_input=False):
        input = 'y' if no_input else ''
        while input != 'y':
            input = raw_input(u'Are you sure you want to rebuild {0} index(es)? [y/N]: '.format(u'the ' + u', '.join(indexes) if indexes else '**ALL**')).lower()
            if input == 'n':
                break

        if input == 'y':
            sys.stdout.write(u"Rebuilding ES indexes: ")
            results, aliases = rebuild_indices(indexes)
            sys.stdout.write(u"complete.\n")
            for alias, index in aliases:
                print u"'{0}' rebuilt and aliased to '{1}'".format(alias, index)

        # TODO: need to offer choice to delete old de-aliased indexes
        # while input != 'y':
        #     input = raw_input(u'Are you sure you want to rebuild {0} index(es)? [y/N]: '.format(u'the ' + u', '.join(indexes) if indexes else '**ALL**')).lower()
        #     if input == 'n':
        #         break
        #
        # if input == 'y':
        #     sys.stdout.write(u"Rebuilding ES indexes: ")
        #     results, aliases = rebuild_indices(indexes)
        #     sys.stdout.write(u"complete.\n")
        #     for alias, index in aliases:
        #         print u"'{0}' rebuilt and aliased to '{1}'".format(alias, index)
