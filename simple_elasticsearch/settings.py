from django.conf import settings


ELASTICSEARCH_SERVER = getattr(settings, 'ELASTICSEARCH_SERVER', ['127.0.0.1:9200', ])
ELASTICSEARCH_CONNECTION_PARAMS = getattr(settings, 'ELASTICSEARCH_CONNECTION_PARAMS', {'hosts': ELASTICSEARCH_SERVER})

# Override this if you want to have a base set of settings for all your indexes. This dictionary
# gets cloned and then updated with custom index-specific from your ELASTICSEARCH_CUSTOM_INDEX_SETTINGS
# Eg. to ensure that all of your indexes have 1 shard and have an edgengram tokenizer/analyzer
# configured
# ELASTICSEARCH_DEFAULT_INDEX_SETTINGS = {
#     "settings" : {
#         "index" : {
#             "number_of_replicas" : 1
#         },
#         "analysis" : {
#             "analyzer" : {
#                 "left" : {
#                     "filter" : [
#                         "standard",
#                         "lowercase",
#                         "stop"
#                     ],
#                     "type" : "custom",
#                     "tokenizer" : "left_tokenizer"
#                 }
#             },
#             "tokenizer" : {
#                 "left_tokenizer" : {
#                     "side" : "front",
#                     "max_gram" : 12,
#                     "type" : "edgeNGram"
#                 }
#             }
#         }
#     }
# }
ELASTICSEARCH_DEFAULT_INDEX_SETTINGS = getattr(settings, 'ELASTICSEARCH_DEFAULT_INDEX_SETTINGS', {})

# Override this in your project settings to define any Elasticsearch-specific index settings.
# Eg.
# ELASTICSEARCH_CUSTOM_INDEX_SETTINGS = {
#     "twitter": {
#         "settings" : {
#             "index" : {
#                 "number_of_shards" : 3,
#             }
#         }
#     },
#     "<your-other-index-name>": {
#         "settings" : {
#             "index" : {
#                 "number_of_shards" : 50,
#                 "number_of_replicas" : 2
#             }
#         }
#     }
# }
ELASTICSEARCH_CUSTOM_INDEX_SETTINGS = getattr(settings, 'ELASTICSEARCH_CUSTOM_INDEX_SETTINGS', {})

# Override this in your project settings, setting it to True, to have
# old indexes deleted on a full rebuild. Currently a new index is
# created, and the alias is switched to the new one from the old, leaving
# old ones on the ES cluster.
ELASTICSEARCH_DELETE_OLD_INDEXES = getattr(settings, 'ELASTICSEARCH_DELETE_OLD_INDEXES', False)
