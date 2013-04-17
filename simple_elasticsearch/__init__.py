from .utils import get_all_indexes

# set up all model post_save signals appropriately
for es_index_name, indexes in get_all_indexes().iteritems():
    for index in indexes:
        index.register_signals()
