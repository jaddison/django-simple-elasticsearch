import django.dispatch


post_indices_create = django.dispatch.Signal(providing_args=["indices", "aliases_set"])
post_indices_rebuild = django.dispatch.Signal(providing_args=["indices", "aliases_set"])
