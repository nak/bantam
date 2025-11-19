import os

import setuptools

VERSION = "2.4.31"

setuptools.setup(
    name='bantam',
    author='John Rusnak',
    author_email='john.j.rusnak@att.net',
    version=VERSION,
    data_files=[('.', ['requirements.txt'])],
    package_data={'': ['requirements.txt', 'LICENSE.txt']},
    description="small utils to automate web interface in Python",
    package_dir={'': 'src'},
    packages=setuptools.find_packages('src'),
    entry_points={
        'console_scripts': [
            'bantam_generate = bantam.autogen.main:main'
        ]
    },
    classifiers=[
                 "Development Status :: 4 - Beta",
                 "License :: OSI Approved :: BSD License"],
    license='BSD 2-CLAUSE',
    keywords='auto web api python',
    url='https://github.com/nak/bantam',
    download_url="https://github.com/bantam/dist/%s" % VERSION,
    install_requires=[
        line for line in open(os.path.join(os.path.dirname(__file__), 'requirements.txt')).read().splitlines() if
         not 'pytest' in line
    ],
    long_description="""
Bantam is a Python package for building http-based micro-services.
It abstracts away any knowledge of routes, mappings and translations
between javascript and Python.  It even provides a means of
auto-generating the javascript client interface to you app
on the fly and serve it to web-based/javascript-based clients.

See https://nak.github.io/bantam_docs/ for details.

    """,
)
