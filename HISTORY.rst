.. :changelog:

History
-------

2.1.6 (2017-03-20)
---------------------

* Allowing direct access (again) to underlying dict/list in `Result` and `Response` classes for serialization and other purposes.

2.1.5 (2017-03-20)
---------------------

* Response class is now MutableSequence based, giving it the properties of a `list`. Its `results` attribute is deprecated, as you can now iterate over the results with the response instance itself.
* Result class `results_meta` is deprecated. Use `meta` instead.
* `get_from_es_or_None` now returns a `Result` object instead of the raw Elasticsearch result, for consistency.
* `get_from_es_or_None` now catches only the Elasticsearch `NotFoundError` exception; previously it caught the more expansive `ElasticsearchException`, which could hide unrelated errors/issues.

2.1.4 (2017-03-12)
---------------------

* Result class is now MutableMapping based, giving it the properties of a `dict`. Its `data` attribute is deprecated.

2.1.3 (2017-03-11)
---------------------

* Minor changes to enable support for elasticsearch-py 5.x.

2.1.0 (2017-03-10)
---------------------

* Addressing a packaging problem which erroneously included pyc/__pycache__ files.

2.0.0 (2016-12-20)
---------------------

* **ALERT: this is a backwards incompatible release**; the old `1.x` (formerly `0.9.x`+) code is maintained on a separate branch for now.
* Added support for Django 1.10.
* Ported delete/cleanup functionality from `1.x`.
* Removed support for Django versions older than 1.8. The goal going forward will be to only support Django versions that the Django core team lists as supported.
* Removed elasticsearch-dsl support: responses and results are now represented by simpler internal representations; queries can ONLY be done via a `dict` form.
* Removed `ElasticsearchForm` - it is easy enough to build a form to validate search input and then form a query `dict` manually.
* Renamed `ElasticsearchIndexMixin` to `ElasticsearchTypeMixin`, seeing as the mixin represented an ES type mapping, not an actual index.
* Renamed `ElasticsearchProcessor` to `SimpleSearch`.
* Overall, this module has been greatly simplified.

1.0.0 (2016-12-20)
---------------------

* Updated 0.9.x codebase version to 1.0.0.
* Reversed decision on the deprecation of the 0.9.x codebase - it will be maintained in this new 1.x branch, although new functionality will mostly occur on newer releases.
* Adding cleanup command to remove unaliased indices.
* Added ELASTICSEARCH_DELETE_OLD_INDEXES setting to auto-remove after a rebuild.
* Thanks to Github user @jimjkelly for the index removal inspiration.

0.9.16 (2015-04-24)
---------------------

* Addressing Django 1.8 warnings.

0.9.15 (2015-01-31)
---------------------

* BUGFIX: Merging pull request from @key that addresses Python 3 support (management command now works).

0.9.14 (2015-01-31)
---------------------

* BUGFIX: Adding in missing `signals.py` file.

0.9.13 (2015-01-30)
---------------------

* Added in new `post_indices_create` and `post_indices_rebuild` signals to allow users to run actions at various points during the index creation and bulk indexing processes.

0.9.12 (2014-12-17)
---------------------

* fixed an issue where per-item request parameters were being added to the bulk data request JSON incorrectly. Tests updated.

0.9.11 (2014-12-08)
---------------------

* added warning if Django's DEBUG=True (causes out of memory errors on constrained
  systems due to Django query caching)
* added index setting modification on rebuilding indices to remove replicas, lucene
  segment merging and disabling the refresh interval - restoring the original
  settings afterwards.

0.9.10 (2014-12-04)
---------------------

* added `page` and `page_size` validation in `add_search()`

0.9.9 (2014-11-24)
---------------------

* Renamed search form related classes - more breaking changes. Added in support
  for Django's pagination classes (internal hack).

0.9.8 (2014-11-23)
---------------------

* Revamped search form related classes - includes breaking changes.

0.9.7 (2014-11-16)
---------------------

* Python3 supported mentioned in PyPi categorization; new testcases added. Minor
  interface change (added `@classmethod`).

0.9.6 (2014-11-16)
---------------------

* Python 3.3+ support, modified (no new) testcases.

0.9.5 (2014-11-15)
---------------------

* Added in tox support, initial set of test cases and verified travis-ci is working.

0.9.2 (2014-11-12)
---------------------

* Fixed broken management command.

0.9.1 (2014-11-10)
---------------------

* Added missing management command module.

0.9.0 (2014-11-10)
---------------------

* In what will become version 1.0, this 0.9.x codebase is a revamp of the
  original codebase (v0.5.x). Completely breaking over previous versions.

0.5.0 (2014-03-05)
---------------------

Final release in 0.x codebase - this old codebase is now unmaintained.
