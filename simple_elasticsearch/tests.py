import contextlib

from django.db.models.signals import post_save, pre_delete
from django.test import TestCase
from elasticsearch import Elasticsearch
import mock

from . import settings as es_settings
from .mixins import ElasticsearchIndexMixin
from .models import Blog, BlogPost


class ElasticsearchIndexMixinClass(ElasticsearchIndexMixin):
    pass


@contextlib.contextmanager
def mock_signal_receiver(signal, wraps=None, **kwargs):
    """
    Borrowed from: https://github.com/dcramer/mock-django/blob/master/mock_django/signals.py

    Temporarily attaches a receiver to the provided ``signal`` within the scope
    of the context manager.
    The mocked receiver is returned as the ``as`` target of the ``with``
    statement.
    To have the mocked receiver wrap a callable, pass the callable as the
    ``wraps`` keyword argument. All other keyword arguments provided are passed
    through to the signal's ``connect`` method.
    >>> with mock_signal_receiver(post_save, sender=Model) as receiver:
    >>>     Model.objects.create()
    >>>     assert receiver.call_count = 1
    """
    if wraps is None:
        wraps = lambda *args, **kwargs: None

    receiver = mock.Mock(wraps=wraps)
    signal.connect(receiver, **kwargs)
    yield receiver
    signal.disconnect(receiver)


class ElasticsearchIndexMixinTestCase(TestCase):
    @property
    def latest_post(self):
        return BlogPost.objects.select_related('blog').latest('id')

    @mock.patch('elasticsearch.Elasticsearch.index')
    def setUp(self, mock_index):
        self.blog = Blog.objects.create(
            name='test blog name',
            description='test blog description'
        )

        # hack the return value to ensure we save some BlogPosts here;
        # without this mock, the post_save handler indexing blows up
        # as there is no real ES instance running
        mock_index.return_value = {}

        post = BlogPost.objects.create(
            blog=self.blog,
            title="DO-NOT-INDEX title",
            slug="DO-NOT-INDEX",
            body="DO-NOT-INDEX body"
        )

        for x in xrange(1, 10):
            BlogPost.objects.create(
                blog=self.blog,
                title="blog post title {0}".format(x),
                slug="blog-post-title-{0}".format(x),
                body="blog post body {0}".format(x)
            )

    def test__get_es__with_default_settings(self):
        result = BlogPost.get_es()
        self.assertIsInstance(result, Elasticsearch)
        self.assertEqual(result.transport.hosts[0]['host'], '127.0.0.1')
        self.assertEqual(result.transport.hosts[0]['port'], 9200)

    def test__get_es__with_custom_server(self):
        # include a custom class here as the internal `_es` is cached, so can't reuse the
        # `ElasticsearchIndexClassDefaults` global class (see above).
        class ElasticsearchIndexClassCustomSettings(ElasticsearchIndexMixin):
            pass

        with self.settings(ELASTICSEARCH_SERVER=['search.example.com:9201']):
            reload(es_settings)
            result = ElasticsearchIndexClassCustomSettings.get_es()
            self.assertIsInstance(result, Elasticsearch)
            self.assertEqual(result.transport.hosts[0]['host'], 'search.example.com')
            self.assertEqual(result.transport.hosts[0]['port'], 9201)

        reload(es_settings)

    def test__get_es__with_custom_connection_settings(self):
        # include a custom class here as the internal `_es` is cached, so can't reuse the
        # `ElasticsearchIndexClassDefaults` global class (see above).
        class ElasticsearchIndexClassCustomSettings(ElasticsearchIndexMixin):
            pass

        with self.settings(ELASTICSEARCH_CONNECTION_PARAMS={'hosts': ['search2.example.com:9202'], 'sniffer_timeout': 15}):
            reload(es_settings)
            result = ElasticsearchIndexClassCustomSettings.get_es()
            self.assertIsInstance(result, Elasticsearch)
            self.assertEqual(result.transport.hosts[0]['host'], 'search2.example.com')
            self.assertEqual(result.transport.hosts[0]['port'], 9202)
            self.assertEqual(result.transport.sniffer_timeout, 15)
        reload(es_settings)

    def test__save_handler(self):
        # with a create call
        with mock_signal_receiver(post_save, sender=BlogPost) as receiver:
            post = BlogPost.objects.create(
                blog=self.blog,
                title="blog post title foo",
                slug="blog-post-title-foo",
                body="blog post body foo"
            )
            self.assertEquals(receiver.call_count, 1)
            self.assertEquals(receiver.call_args[1]['sender'], BlogPost)
            self.assertEquals(receiver.call_args[1]['instance'], post)

        # with a plain save call
        with mock_signal_receiver(post_save, sender=BlogPost) as receiver:
            post.save()
            self.assertEquals(receiver.call_count, 1)
            self.assertEquals(receiver.call_args[1]['sender'], BlogPost)
            self.assertEquals(receiver.call_args[1]['instance'], post)

    def test__delete_handler(self):
        with mock_signal_receiver(pre_delete, sender=BlogPost) as receiver:
            post = self.latest_post
            post.delete()
            self.assertEquals(receiver.call_count, 1)
            self.assertEquals(receiver.call_args[1]['sender'], BlogPost)
            self.assertEquals(receiver.call_args[1]['instance'], post)

    @mock.patch('elasticsearch.Elasticsearch.index')
    def test__index_add(self, mock_index):
        post = self.latest_post
        mock_index.return_value = {}

        # make sure an invalid object passed in returns False
        result = BlogPost.index_add(None)
        self.assertFalse(result)

        # make sure indexing an item calls Elasticsearch.index() with
        # the correct variables, with normal index name
        result = BlogPost.index_add(post)
        self.assertTrue(result)
        mock_index.assert_called_with('blog', 'posts', BlogPost.get_document(post), post.pk)

        # make sure indexing an item calls Elasticsearch.index() with
        # the correct variables, with non-standard index name
        result = BlogPost.index_add(post, 'foo')
        self.assertTrue(result)
        mock_index.assert_called_with('foo', 'posts', BlogPost.get_document(post), post.pk)

        # this one should not index (return false) because the
        # 'should_index' for this post should make it skip it
        post = BlogPost.objects.get(slug="DO-NOT-INDEX")
        result = BlogPost.index_add(post)
        self.assertFalse(result)

    @mock.patch('elasticsearch.Elasticsearch.delete')
    def test__index_delete(self, mock_delete):
        post = self.latest_post
        mock_delete.return_value = {
            "acknowledged": True
        }

        # make sure an invalid object passed in returns False
        result = BlogPost.index_delete(None)
        self.assertFalse(result)

        # make sure deleting an item calls Elasticsearch.delete() with
        # the correct variables, with normal index name
        result = BlogPost.index_delete(post)
        self.assertTrue(result)
        mock_delete.assert_called_with('blog', 'posts', post.pk)

        # make sure deleting an item calls Elasticsearch.delete() with
        # the correct variables, with non-standard index name
        result = BlogPost.index_delete(post, 'foo')
        self.assertTrue(result)
        mock_delete.assert_called_with('foo', 'posts', post.pk)

    @mock.patch('simple_elasticsearch.mixins.ElasticsearchIndexMixin.index_add')
    @mock.patch('simple_elasticsearch.mixins.ElasticsearchIndexMixin.index_delete')
    def test__index_add_or_delete(self, mock_index_delete, mock_index_add):
        # invalid object passed in, should return False
        result = BlogPost.index_add_or_delete(None)
        self.assertFalse(result)

        # this one should not index (return false) because the
        # `should_index` for this post should make it skip it;
        # `index_delete` should get called
        mock_index_delete.return_value = True
        post = BlogPost.objects.get(slug="DO-NOT-INDEX")

        result = BlogPost.index_add_or_delete(post)
        self.assertTrue(result)
        mock_index_delete.assert_called_with(post, '')

        result = BlogPost.index_add_or_delete(post, 'foo')
        self.assertTrue(result)
        mock_index_delete.assert_called_with(post, 'foo')

        # `index_add` call results below
        mock_index_add.return_value = True
        post = self.latest_post

        result = BlogPost.index_add_or_delete(post)
        self.assertTrue(result)
        mock_index_add.assert_called_with(post, '')

        result = BlogPost.index_add_or_delete(post, 'foo')
        self.assertTrue(result)
        mock_index_add.assert_called_with(post, 'foo')


    def test__get_index_name(self):
        self.assertEquals(BlogPost.get_index_name(), 'blog')

    def test__get_type_name(self):
        self.assertEquals(BlogPost.get_type_name(), 'posts')

    def test__get_queryset(self):
        queryset = BlogPost.objects.all().select_related('blog').order_by('pk')
        self.assertEquals(list(BlogPost.get_queryset().order_by('pk')), list(queryset))

    def test__get_index_name_notimplemented(self):
        with self.assertRaises(NotImplementedError):
            ElasticsearchIndexMixinClass.get_index_name()

    def test__get_type_name_notimplemented(self):
        with self.assertRaises(NotImplementedError):
            ElasticsearchIndexMixinClass.get_type_name()

    def test__get_queryset_notimplemented(self):
        with self.assertRaises(NotImplementedError):
            ElasticsearchIndexMixinClass.get_queryset()

    def test__get_type_mapping(self):
        mapping = {
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
        self.assertEquals(BlogPost.get_type_mapping(), mapping)

    def test__get_type_mapping_notimplemented(self):
        self.assertEquals(ElasticsearchIndexMixinClass.get_type_mapping(), {})

    def test__get_request_params(self):
        post = self.latest_post
        # TODO: implement the method to test it works properly
        self.assertEquals(BlogPost.get_request_params(post), {})

    def test__get_request_params_notimplemented(self):
        self.assertEquals(ElasticsearchIndexMixinClass.get_request_params(1), {})

    def test__get_bulk_index_limit(self):
        self.assertTrue(str(BlogPost.get_bulk_index_limit()).isdigit())

    def test__get_document_id(self):
        post = self.latest_post
        result = BlogPost.get_document_id(post)
        self.assertEquals(result, post.pk)

    def test__get_document(self):
        post = self.latest_post
        result = BlogPost.get_document(post)
        self.assertEquals(result, {
            'title': post.title,
            'slug': post.slug,
            'blog': {
                'id': post.blog.pk,
                'description': post.blog.description,
                'name': post.blog.name
            },
            'created_at': post.created_at,
            'body': post.body
        })

    def test__get_document_notimplemented(self):
        with self.assertRaises(NotImplementedError):
            ElasticsearchIndexMixinClass.get_document(1)

    @mock.patch('elasticsearch.Elasticsearch.index')
    def test__should_index(self, mock_index):
        post = self.latest_post
        self.assertTrue(BlogPost.should_index(post))

        mock_index.return_value = {}
        post = BlogPost.objects.get(slug="DO-NOT-INDEX")
        self.assertFalse(BlogPost.should_index(post))

    def test__should_index_notimplemented(self):
        self.assertTrue(ElasticsearchIndexMixinClass.should_index(1))
