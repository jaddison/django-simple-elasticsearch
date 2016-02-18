Usage
=====

For a minimal investment of time, Django Simple Elasticsearch offers a number of perks. Implementing a class
with the :code:`ElasticsearchTypeMixin` lets you:

* initialize your Elasticsearch indices and mappings via the included :code:`es_manage` management command
* perform Elasticsearch bulk indexing via the same :code:`es_manage` management command
* perform Elasticsearch bulk indexing as well as individual index/delete requests on demand in your code
* connect the available :code:`ElasticsearchTypeMixin` save and delete handlers to Django's available
  model signals (ie :code:`post_save`, :code:`post_delete`)

Let's look at an example implementation of :code:`ElasticsearchTypeMixin`. Here's a couple of blog-related Models
in a :code:`models.py` file:

.. code-block:: python

    class Blog(models.Model):
        name = models.CharField(max_length=50)
        description = models.TextField()

    class BlogPost(models.Model):
        blog = models.ForeignKey(Blog)
        slug = models.SlugField()
        title = models.CharField(max_length=50)
        body = models.TextField()
        created_at = models.DateTimeField(auto_now_add=True)

To start with :code:`simple_elasticsearch`, you'll need to tell it that the :code:`BlogPost` class implements the
:code:`ElasticsearchTypeMixin` mixin, so in your :code:`settings.py` set the :code:`ELASTICSEARCH_TYPE_CLASSES` setting:

.. code-block:: python

    ELASTICSEARCH_TYPE_CLASSES = [
        'blog.models.BlogPost'
    ]

If you do not add this setting, everything will still work except for the :code:`es_manage` command - it won't know
what indices to create, type mappings to set or what objects to index. As you add additional
:code:`ElasticsearchTypeMixin`-based index handlers, add them to this list.

All right, let's add in :code:`ElasticsearchTypeMixin` to the :code:`BlogPost` model. Only pertinent changes from the
above :code:`models.py` are shown:

.. code-block:: python

    from simple_elasticsearch.mixins import ElasticsearchTypeMixin

    ...

    class BlogPost(models.Model, ElasticsearchTypeMixin):
        blog = models.ForeignKey(Blog)
        slug = models.SlugField()
        title = models.CharField(max_length=50)
        body = models.TextField()
        created_at = models.DateTimeField(auto_now_add=True)

        @classmethod
        def get_queryset(cls):
            return BlogPost.objects.all().select_related('blog')

        @classmethod
        def get_index_name(cls):
            return 'blog'

        @classmethod
        def get_type_name(cls):
            return 'posts'

        @classmethod
        def get_type_mapping(cls):
            return {
                "properties": {
                    "created_at": {
                        "type": "date",
                        "format": "dateOptionalTime"
                    },
                    "title": {
                        "type": "string"
                    },
                    "body": {
                        "type": "string"
                    },
                    "slug": {
                        "type": "string"
                    },
                    "blog": {
                        "properties": {
                            "id": {
                                "type": "long"
                            },
                            "name": {
                                "type": "string"
                            },
                            "description": {
                                "type": "string"
                            }
                        }
                    }
                }
            }

        @classmethod
        def get_document(cls, obj):
            return {
                'created_at': obj.created_at,
                'title': obj.title,
                'body': obj.body,
                'slug': obj.slug,
                'blog': {
                    'id': obj.blog.id,
                    'name': obj.blog.name,
                    'description': obj.blog.description,
                }
            }

With this mixin implementation, you can now use the :code:`es_manage` management command to bulk reindex all :code:`BlogPost`
items. Note that there are additional :code:`@classmethods` you can override to customize functionality. Sane defaults
have been provided for these - see the source for details.

Of course, our :code:`BlogPost` implementation doesn't ensure that your Elasticsearch index is updated every time you
save or delete - for this, you can use the :code:`ElasticsearchTypeMixin` built-in save and delete handlers.

.. code-block:: python

    from django.db.models.signals import post_save, pre_delete

    ...

    post_save.connect(BlogPost.save_handler, sender=BlogPost)
    pre_delete.connect(BlogPost.delete_handler, sender=BlogPost)

Awesome - Django's magic is applied.

TODO:

* add examples for more complex data situations
* add examples of using :code:`es_manage` management command options
* add examples/scenarios when to use :code:`post_indices_create` and :code:`post_indices_rebuild` signals (ie. adding percolators to new indices)
