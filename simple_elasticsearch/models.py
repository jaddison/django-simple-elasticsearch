from django.conf import settings


if getattr(settings, 'IS_TEST', False):
    from django.db import models
    from django.db.models.signals import post_save, pre_delete

    from .mixins import ElasticsearchTypeMixin

    class Blog(models.Model):
        name = models.CharField(max_length=50)
        description = models.TextField()

    class BlogPost(models.Model, ElasticsearchTypeMixin):
        blog = models.ForeignKey(Blog)
        slug = models.SlugField()
        title = models.CharField(max_length=50)
        body = models.TextField()
        created_at = models.DateTimeField(auto_now_add=True)
        bulk_ordering = 'pk'

        @classmethod
        def get_bulk_ordering(cls):
            return cls.bulk_ordering

        @classmethod
        def get_bulk_index_limit(cls):
            return 2

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
        def get_request_params(cls, obj):
            return {'routing': obj.blog_id}

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

        @classmethod
        def should_index(cls, obj):
            return obj.slug != 'DO-NOT-INDEX'

    post_save.connect(BlogPost.save_handler, sender=BlogPost)
    pre_delete.connect(BlogPost.delete_handler, sender=BlogPost)
