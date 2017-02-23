===========================
Django Simple Elasticsearch
===========================

.. image:: https://badge.fury.io/py/django-simple-elasticsearch.png
  :target: http://badge.fury.io/py/django-simple-elasticsearch

.. image:: https://travis-ci.org/jaddison/django-simple-elasticsearch.png?branch=1.x
  :target: https://travis-ci.org/jaddison/django-simple-elasticsearch

.. image:: https://coveralls.io/repos/jaddison/django-simple-elasticsearch/badge.png
  :target: https://coveralls.io/r/jaddison/django-simple-elasticsearch


This package provides a simple method of creating Elasticsearch indexes for
Django models.

-----

Versions
--------

Branch :code:`master` targets both Elasticsearch 2.x and 5.x and will receive new
features. Both `elasticsearch-py` 2.x and 5.x Python modules are currently
supported. `Documentation <http://django-simple-elasticsearch.readthedocs.io/>`_

Branch :code:`1.x` is the maintenance branch for the legacy 0.9.x versioned releases,
which targeted Elasticsearch versions less than 2.0. This branch is unlikely to
receive new features, but will receive required fixes.
`Documentation <http://django-simple-elasticsearch.readthedocs.io/en/1.x/>`_

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

Configuring
-----------

Add the simple_elasticsearch application to your INSTALLED_APPS list::

    INSTALLED_APPS = (
        ...
        'simple_elasticsearch',
    )

Add any models to `ELASTICSEARCH_TYPE_CLASSES` setting for indexing using **es_manage** management command::

    ELASTICSEARCH_TYPE_CLASSES = [
        'blog.models.BlogPost'
    ]

License
-------

**django-simple-elasticsearch** is licensed as free software under the BSD license.

Todo
----

* Review search classes - simplify functionality where possible. This may cause breaking changes.
* Tests. Write them.
* Documentation. Write it.
