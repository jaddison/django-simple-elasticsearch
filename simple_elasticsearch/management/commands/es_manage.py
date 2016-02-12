import sys
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ...utils import get_indices, create_indices, rebuild_indices, delete_indices

try:
    raw_input
except NameError:
    raw_input = input


class Unbuffered(object):
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    def __getattr__(self, attr):
        return getattr(self.stream, attr)
sys.stdout = Unbuffered(sys.stdout)


class ESCommandError(CommandError):
    pass


class Command(BaseCommand):
    help = ''

    def add_arguments(self, parser):
        parser.add_argument('--list', action='store_true', dest='list', default=False)
        parser.add_argument('--initialize', action='store_true', dest='initialize', default=False)
        parser.add_argument('--rebuild', action='store_true', dest='rebuild', default=False)
        parser.add_argument('--cleanup', action='store_true', dest='cleanup', default=False)
        parser.add_argument('--no_input', '--noinput', action='store_true', dest='no_input', default=False)
        parser.add_argument('--indexes', action='store', dest='indexes', default='')

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
        elif options.get('cleanup'):
            self.subcommand_cleanup(requested_indexes, no_input)

    def subcommand_list(self):
        print("Available ES indexes:")
        for index_name, type_classes in get_indices().items():
            print(" - index '{0}':".format(index_name))
            for type_class in type_classes:
                print("  - type '{0}'".format(type_class.get_type_name()))

    def subcommand_initialize(self, indexes=None, no_input=False):
        user_input = 'y' if no_input else ''
        while user_input != 'y':
            user_input = raw_input('Are you sure you want to initialize {0} index(es)? [y/N]: '.format('the ' + ', '.join(indexes) if indexes else '**ALL**')).lower()
            if user_input == 'n':
                break

        if user_input == 'y':
            sys.stdout.write("Creating ES indexes: ")
            results, aliases = create_indices(indices=indexes)
            sys.stdout.write("complete.\n")
            for alias, index in aliases:
                print("'{0}' aliased to '{1}'".format(alias, index))

    def subcommand_cleanup(self, indexes=None, no_input=False):
        user_input = 'y' if no_input else ''
        while user_input != 'y':
            user_input = raw_input('Are you sure you want to clean up (ie DELETE) {0} index(es)? [y/N]: '.format('the ' + ', '.join(indexes) if indexes else '**ALL**')).lower()
            if user_input == 'n':
                break

        if user_input == 'y':
            sys.stdout.write("Deleting ES indexes: ")
            indices = delete_indices(indices=indexes)
            sys.stdout.write("complete.\n")
            for index in indices:
                print("'{0}' index deleted".format(index))
            else:
                print("{0} removed.".format(len(indices)))

    def subcommand_rebuild(self, indexes, no_input=False):
        if getattr(settings, 'DEBUG', False):
            import warnings
            warnings.warn('Rebuilding with `settings.DEBUG = True` can result in out of memory crashes. See https://docs.djangoproject.com/en/stable/ref/settings/#debug', stacklevel=2)

            # make sure the user continues explicitly after seeing this warning
            no_input = False

        user_input = 'y' if no_input else ''
        while user_input != 'y':
            user_input = raw_input('Are you sure you want to rebuild {0} index(es)? [y/N]: '.format('the ' + ', '.join(indexes) if indexes else '**ALL**')).lower()
            if user_input in ['n', '']:
                break

        if user_input == 'y':
            sys.stdout.write("Rebuilding ES indexes: ")
            results, aliases = rebuild_indices(indices=indexes)
            sys.stdout.write("complete.\n")
            for alias, index in aliases:
                print("'{0}' rebuilt and aliased to '{1}'".format(alias, index))
        else:
            print("You chose not to rebuild indices.")
