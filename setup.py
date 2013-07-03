from distutils.core import setup


setup(
    name = 'django-simple-elasticsearch',
    description = 'Simple Django ElasticSearch indexing integration.',
    long_description=u'View `django-simple-elasticsearch documentation on Github  <https://github.com/jaddison/django-simple-elasticsearch>`_.',
    author='James Addison',
    author_email='code@scottisheyes.com',
    packages = [
        'simple_elasticsearch',
        'simple_elasticsearch.management',
        'simple_elasticsearch.management.commands'
    ],
    version = '0.1.3',
    url='http://github.com/jaddison/django-simple-elasticsearch',
    keywords=['search', 'django', 'elasticsearch', 'es', 'index'],
    license='BSD',
    requires=['pyelasticsearch'],
    classifiers=[
      'Development Status :: 4 - Beta',
      'License :: OSI Approved :: BSD License',
      'Intended Audience :: Developers',
      'Environment :: Web Environment',
      'Programming Language :: Python',
      'Framework :: Django',
      'Topic :: Internet :: WWW/HTTP :: WSGI',
    ],
)