===========================
Django Simple Elasticsearch
===========================

.. image:: https://badge.fury.io/py/django-simple-elasticsearch.png
  :target: http://badge.fury.io/py/django-simple-elasticsearch

.. image:: https://travis-ci.org/jaddison/django-simple-elasticsearch.png?branch=master
  :target: https://travis-ci.org/jaddison/django-simple-elasticsearch

.. image:: https://coveralls.io/repos/jaddison/django-simple-elasticsearch/badge.png
  :target: https://coveralls.io/r/jaddison/django-simple-elasticsearch

.. image:: https://pypip.in/d/django-simple-elasticsearch/badge.png
  :target: https://pypi.python.org/pypi/django-simple-elasticsearch


This package provides a simple method of creating Elasticsearch indexes for
Django models.

**Using a version older than 0.9.0? Please be aware that as of v0.9.0, this package
has changed in a backwards-incompatible manner. Version 0.5 is deprecated and no
longer maintained.**

-----

Documentation
-------------

Visit the `django-simple-elasticsearch documentation on ReadTheDocs <http://django-simple-elasticsearch.readthedocs.org/>`_.

Features
--------

* class mixin with a set of :code:`@classmethods` used to handle:
 * type mapping definition
 * individual object indexing and deletion
 * bulk object indexing
 * model signal handlers for pre/post_save and pre/post_delete (optional)
* management command to handle index/type mapping initialization and bulk indexing
 * uses Elasticsearch aliases to ease the burden of re-indexing
* small set of Django classes and functions to help deal with Elasticsearch querying
 * base search form class to handle input validation, query preparation and response handling
 * multi-search processor class to batch multiple Elasticsearch queries via :code:`_msearch`
 * 'get' shortcut functions
* post index create/rebuild signals available to perform actions after certain stages (ie. add your own percolators)

Installation
------------

At the command line::

    $ easy_install django-simple-elasticsearch

Or::

    $ pip install django-simple-elasticsearch

License
-------

**django-simple-elasticsearch** is licensed as free software under the BSD license.

Todo
----

* Review search classes - simplify functionality where possible. This may cause breaking changes.
* Tests. Write them.
* Documentation. Write it.
