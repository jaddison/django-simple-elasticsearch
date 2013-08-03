from django.conf import settings


# Using this causes the ESDirectMixin and ESRabbitMQMixin to temporarily store ES bulk-formatted
# index/delete requests from save/delete signal calls until the request has been sent to the client
# and then sends them to the broker/task/ES. This ensures that client response times are affected
# as little as possible.
ES_USE_REQUEST_FINISHED_SIGNAL = getattr(settings, 'ES_USE_REQUEST_FINISHED_SIGNAL', False)
ES_BULK_LIMIT_BEFORE_SEND = getattr(settings, 'ES_BULK_LIMIT_BEFORE_SEND', 500)
ES_CONNECTION_URL = getattr(settings, 'ES_CONNECTION_URL', 'http://localhost:9200/')

# Override this if you want to have a base set of settings for all your indexes. This dictionary
# gets cloned and then updated with custom index-specific from your ES_CUSTOM_INDEX_SETTINGS
# Eg. to ensure that all of your indexes have 1 shard and have an edgengram tokenizer/analyzer
# configured
# ES_DEFAULT_INDEX_SETTINGS = {
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
ES_DEFAULT_INDEX_SETTINGS = getattr(settings, 'ES_DEFAULT_INDEX_SETTINGS', {})

# Override this in your project settings to define any ElasticSearch-specific index settings.
# Eg.
# ES_CUSTOM_INDEX_SETTINGS = {
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
ES_CUSTOM_INDEX_SETTINGS = getattr(settings, 'ES_CUSTOM_INDEX_SETTINGS', {})
