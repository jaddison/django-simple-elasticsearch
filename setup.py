from setuptools import setup, find_packages

try:
    import pypandoc
    description_files = [
        'README.md',
        'HISTORY.md',
        'AUTHORS.md',
        'CONTRIBUTING.md'
    ]

    long_description = u''
    for f in description_files:
        try:
            long_description += pypandoc.convert(f, 'rst') + '\n\n'
        except IOError:
            pass
except ImportError:
    long_description = u'View `django-simple-elasticsearch documentation on Github  <https://github.com/jaddison/django-simple-elasticsearch>`_.'


setup(
    name = 'django-simple-elasticsearch',
    version='0.1.10',
    description = 'Simple Django ElasticSearch indexing integration.',
    long_description=long_description,
    url='http://github.com/jaddison/django-simple-elasticsearch',
    license='BSD',
    author='James Addison',
    author_email='code@scottisheyes.com',
    packages=find_packages(exclude=['tests*']),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Intended Audience :: Developers',
        'Environment :: Web Environment',
        'Programming Language :: Python',
        'Framework :: Django',
        'Topic :: Internet :: WWW/HTTP :: WSGI'
    ]
)
