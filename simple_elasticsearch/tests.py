import copy
from datadiff import tools as ddtools
from django.core.paginator import Page
from django.test import TestCase
from elasticsearch import Elasticsearch
import mock

try:
    # `reload` is not a python3 builtin like python2
    reload
except NameError:
    from imp import reload

from . import settings as es_settings
from .search import SimpleSearch
from .mixins import ElasticsearchTypeMixin
from .models import Blog, BlogPost


class ElasticsearchTypeMixinClass(ElasticsearchTypeMixin):
    pass


class ElasticsearchTypeMixinTestCase(TestCase):

    @property
    def latest_post(self):
        return BlogPost.objects.select_related('blog').latest('id')

    @mock.patch('simple_elasticsearch.mixins.Elasticsearch.delete')
    @mock.patch('simple_elasticsearch.mixins.Elasticsearch.index')
    def setUp(self, mock_index, mock_delete):
        self.blog = Blog.objects.create(
            name='test blog name',
            description='test blog description'
        )

        # hack the return value to ensure we save some BlogPosts here;
        # without this mock, the post_save handler indexing blows up
        # as there is no real ES instance running
        mock_index.return_value = mock_delete.return_value = {}

        post = BlogPost.objects.create(
            blog=self.blog,
            title="DO-NOT-INDEX title",
            slug="DO-NOT-INDEX",
            body="DO-NOT-INDEX body"
        )

        for x in range(1, 10):
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
        class ElasticsearchIndexClassCustomSettings(ElasticsearchTypeMixin):
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
        class ElasticsearchIndexClassCustomSettings(ElasticsearchTypeMixin):
            pass

        with self.settings(ELASTICSEARCH_CONNECTION_PARAMS={'hosts': ['search2.example.com:9202'], 'sniffer_timeout': 15}):
            reload(es_settings)
            result = ElasticsearchIndexClassCustomSettings.get_es()
            self.assertIsInstance(result, Elasticsearch)
            self.assertEqual(result.transport.hosts[0]['host'], 'search2.example.com')
            self.assertEqual(result.transport.hosts[0]['port'], 9202)
            self.assertEqual(result.transport.sniffer_timeout, 15)
        reload(es_settings)

    @mock.patch('simple_elasticsearch.mixins.ElasticsearchTypeMixin.index_add_or_delete')
    def test__save_handler(self, mock_index_add_or_delete):
        # with a create call
        post = BlogPost.objects.create(
            blog=self.blog,
            title="blog post title foo",
            slug="blog-post-title-foo",
            body="blog post body foo"
        )
        mock_index_add_or_delete.assert_called_with(post)
        mock_index_add_or_delete.reset_mock()

        # with a plain save call
        post.save()
        mock_index_add_or_delete.assert_called_with(post)

    @mock.patch('simple_elasticsearch.mixins.ElasticsearchTypeMixin.index_delete')
    def test__delete_handler(self, mock_index_delete):
        post = self.latest_post
        post.delete()
        mock_index_delete.assert_called_with(post)

    @mock.patch('simple_elasticsearch.mixins.Elasticsearch.index')
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
        mock_index.assert_called_with('blog', 'posts', BlogPost.get_document(post), post.pk, routing=1)

        # make sure indexing an item calls Elasticsearch.index() with
        # the correct variables, with non-standard index name
        result = BlogPost.index_add(post, 'foo')
        self.assertTrue(result)
        mock_index.assert_called_with('foo', 'posts', BlogPost.get_document(post), post.pk, routing=1)

        # this one should not index (return false) because the
        # 'should_index' for this post should make it skip it
        post = BlogPost.objects.get(slug="DO-NOT-INDEX")
        result = BlogPost.index_add(post)
        self.assertFalse(result)

    @mock.patch('simple_elasticsearch.mixins.Elasticsearch.delete')
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
        mock_delete.assert_called_with('blog', 'posts', post.pk, routing=1)

        # make sure deleting an item calls Elasticsearch.delete() with
        # the correct variables, with non-standard index name
        result = BlogPost.index_delete(post, 'foo')
        self.assertTrue(result)
        mock_delete.assert_called_with('foo', 'posts', post.pk, routing=1)

    @mock.patch('simple_elasticsearch.mixins.ElasticsearchTypeMixin.index_add')
    @mock.patch('simple_elasticsearch.mixins.ElasticsearchTypeMixin.index_delete')
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
        self.assertEqual(BlogPost.get_index_name(), 'blog')

    def test__get_type_name(self):
        self.assertEqual(BlogPost.get_type_name(), 'posts')

    def test__get_queryset(self):
        queryset = BlogPost.objects.all().select_related('blog').order_by('pk')
        self.assertEqual(list(BlogPost.get_queryset().order_by('pk')), list(queryset))

    def test__get_index_name_notimplemented(self):
        with self.assertRaises(NotImplementedError):
            ElasticsearchTypeMixinClass.get_index_name()

    def test__get_type_name_notimplemented(self):
        with self.assertRaises(NotImplementedError):
            ElasticsearchTypeMixinClass.get_type_name()

    def test__get_queryset_notimplemented(self):
        with self.assertRaises(NotImplementedError):
            ElasticsearchTypeMixinClass.get_queryset()

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
        self.assertEqual(BlogPost.get_type_mapping(), mapping)

    def test__get_type_mapping_notimplemented(self):
        self.assertEqual(ElasticsearchTypeMixinClass.get_type_mapping(), {})

    def test__get_request_params(self):
        post = self.latest_post
        # TODO: implement the method to test it works properly
        self.assertEqual(BlogPost.get_request_params(post), {'routing':1})

    def test__get_request_params_notimplemented(self):
        self.assertEqual(ElasticsearchTypeMixinClass.get_request_params(1), {})

    def test__get_bulk_index_limit(self):
        self.assertTrue(str(BlogPost.get_bulk_index_limit()).isdigit())

    def test__get_query_limit(self):
        self.assertTrue(str(BlogPost.get_query_limit()).isdigit())

    def test__get_document_id(self):
        post = self.latest_post
        result = BlogPost.get_document_id(post)
        self.assertEqual(result, post.pk)

    def test__get_document(self):
        post = self.latest_post
        result = BlogPost.get_document(post)
        self.assertEqual(result, {
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
            ElasticsearchTypeMixinClass.get_document(1)

    @mock.patch('simple_elasticsearch.mixins.Elasticsearch.index')
    def test__should_index(self, mock_index):
        post = self.latest_post
        self.assertTrue(BlogPost.should_index(post))

        mock_index.return_value = {}
        post = BlogPost.objects.get(slug="DO-NOT-INDEX")
        self.assertFalse(BlogPost.should_index(post))

    def test__should_index_notimplemented(self):
        self.assertTrue(ElasticsearchTypeMixinClass.should_index(1))

    @mock.patch('simple_elasticsearch.mixins.queryset_iterator')
    def test__bulk_index_queryset(self, mock_queryset_iterator):
        queryset = BlogPost.get_queryset().exclude(slug='DO-NOT-INDEX')
        BlogPost.bulk_index(queryset=queryset)
        mock_queryset_iterator.assert_called_with(queryset, BlogPost.get_query_limit(), 'pk')

        mock_queryset_iterator.reset_mock()

        queryset = BlogPost.get_queryset()
        BlogPost.bulk_index()
        # to compare QuerySets, they must first be converted to lists.
        self.assertEqual(list(mock_queryset_iterator.call_args[0][0]), list(queryset))

        mock_queryset_iterator.reset_mock()

        # hack in a test for ensuring the proper bulk ordering is used
        BlogPost.bulk_ordering = 'created_at'
        BlogPost.bulk_index(queryset=queryset)
        mock_queryset_iterator.assert_called_with(queryset, BlogPost.get_query_limit(), 'created_at')
        BlogPost.bulk_ordering = 'pk'


    @mock.patch('simple_elasticsearch.models.BlogPost.get_document')
    @mock.patch('simple_elasticsearch.models.BlogPost.should_index')
    @mock.patch('simple_elasticsearch.mixins.Elasticsearch.bulk')
    def test__bulk_index_should_index(self, mock_bulk, mock_should_index, mock_get_document):
        # hack the return value to ensure we save some BlogPosts here;
        # without this mock, the post_save handler indexing blows up
        # as there is no real ES instance running
        mock_bulk.return_value = {}

        queryset_count = BlogPost.get_queryset().count()
        BlogPost.bulk_index()
        self.assertTrue(mock_should_index.call_count == queryset_count)

    @mock.patch('simple_elasticsearch.models.BlogPost.get_document')
    @mock.patch('simple_elasticsearch.mixins.Elasticsearch.bulk')
    def test__bulk_index_get_document(self, mock_bulk, mock_get_document):
        mock_bulk.return_value = mock_get_document.return_value = {}

        queryset_count = BlogPost.get_queryset().count()
        BlogPost.bulk_index()

        # One of the items is not meant to be indexed (slug='DO-NOT-INDEX'), so the
        # get_document function will get called one less time due to this.
        self.assertTrue(mock_get_document.call_count == (queryset_count - 1))

    @mock.patch('simple_elasticsearch.mixins.Elasticsearch.bulk')
    def test__bulk_index_bulk(self, mock_bulk):
        mock_bulk.return_value = {}

        queryset_count = BlogPost.get_queryset().count()
        BlogPost.bulk_index()

        # figure out how many times es.bulk() should get called in the
        # .bulk_index() method and verify it's the same
        bulk_times = int(queryset_count / BlogPost.get_bulk_index_limit()) + 1
        self.assertTrue(mock_bulk.call_count == bulk_times)


class SimpleSearchTestCase(TestCase):

    def setUp(self):
        self.query = {'q': 'python'}

    def test__esp_reset(self):
        esp = SimpleSearch()

        self.assertTrue(len(esp.bulk_search_data) == 0)
        self.assertTrue(len(esp.page_ranges) == 0)

        esp.add_search({
            "query": {
                "match": {
                    "_all": "foobar"
                }
            }
        })

        self.assertFalse(len(esp.bulk_search_data) == 0)
        self.assertFalse(len(esp.page_ranges) == 0)

        esp.reset()

        self.assertTrue(len(esp.bulk_search_data) == 0)
        self.assertTrue(len(esp.page_ranges) == 0)

    def test__esp_add_query_dict(self):
        esp = SimpleSearch()

        page = 1
        page_size = 20

        query = {
            "query": {
                "match": {
                    "_all": "foobar"
                }
            }
        }

        # SimpleSearch internally sets the from/size parameters
        # on the query; we need to compare with those values included
        query_with_size = query.copy()
        query_with_size.update({
            'from': (page - 1) * page_size,
            'size': page_size
        })

        esp.add_search(query.copy())
        ddtools.assert_equal(esp.bulk_search_data[0], {})
        ddtools.assert_equal(esp.bulk_search_data[1], query_with_size)

        esp.reset()
        esp.add_search(query.copy(), index='blog')
        ddtools.assert_equal(esp.bulk_search_data[0], {'index': 'blog'})
        ddtools.assert_equal(esp.bulk_search_data[1], query_with_size)

        esp.reset()
        esp.add_search(query.copy(), index='blog', doc_type='posts')
        ddtools.assert_equal(esp.bulk_search_data[0], {'index': 'blog', 'type': 'posts'})
        ddtools.assert_equal(esp.bulk_search_data[1], query_with_size)

    @mock.patch('simple_elasticsearch.search.Elasticsearch.msearch')
    def test__esp_search(self, mock_msearch):
        mock_msearch.return_value = {
            "responses": [
                {
                    "hits": {
                        "total": 20,
                        "hits": [
                            {
                                "_index": "blog",
                                "_type": "posts",
                                "_id": "1",
                                "_score": 1.0,
                                "_source": {"account_number": 1,}
                            }, {
                                "_index": "blog",
                                "_type": "posts",
                                "_id": "6",
                                "_score": 1.0,
                                "_source": {"account_number": 6,}
                            }
                        ]
                    }
                }
            ]
        }

        esp = SimpleSearch()
        esp.add_search({}, 3, 2, index='blog', doc_type='posts')

        bulk_data = copy.deepcopy(esp.bulk_search_data)
        ddtools.assert_equal(bulk_data, [{'index': 'blog', 'type': 'posts'}, {'from': 4, 'size': 2}])

        responses = esp.search()
        mock_msearch.assert_called_with(bulk_data)

        # ensure that our hack to get size and from into the hit
        # data works
        self.assertEqual(responses[0]._page_num, 3)
        self.assertEqual(responses[0]._page_size, 2)

        # ensure that the bulk data gets reset
        self.assertEqual(len(esp.bulk_search_data), 0)

        page = responses[0].page
        self.assertIsInstance(page, Page)
        self.assertEqual(page.number, 3)
        self.assertTrue(page.has_next())
        self.assertTrue(page.has_previous())
        self.assertEqual(len(list(page)), 2)  # 2 items on the page

    @mock.patch('simple_elasticsearch.search.Elasticsearch.msearch')
    def test__esp_search2(self, mock_msearch):
        mock_msearch.return_value = {
            "responses": [
                {
                    "hits": {
                        "total": 20,
                        "hits": [
                            {
                                "_index": "blog",
                                "_type": "posts",
                                "_id": "1",
                                "_score": 1.0,
                                "_source": {"account_number": 1,}
                            }, {
                                "_index": "blog",
                                "_type": "posts",
                                "_id": "6",
                                "_score": 1.0,
                                "_source": {"account_number": 6,}
                            }
                        ]
                    }
                }
            ]
        }

        esp = SimpleSearch()
        esp.add_search({}, 1, 2, index='blog', doc_type='posts')
        responses = esp.search()
        page = responses[0].page
        self.assertTrue(page.has_next())
        self.assertFalse(page.has_previous())
