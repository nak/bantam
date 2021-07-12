import os

import setuptools

VERSION = "0.6.5"

setuptools.setup(
    name='bantam',
    author='John Rusnak',
    author_email='john.j.rusnak@att.net',
    version=VERSION,

    description="small utils to automate web interface in Python",
    package_dir={'': 'src'},
    packages=setuptools.find_packages('src'),
    entry_points={
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
    ]
)
