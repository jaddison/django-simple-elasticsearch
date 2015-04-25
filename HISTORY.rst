.. :changelog:

History
-------

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