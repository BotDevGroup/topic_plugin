#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

requirements = [
    'marvinbot'
]

test_requirements = [
]

setup(
    name='topic_plugin',
    version='0.1.0',
    description="A plugin for marvinbot to manage group/supergroup chat titles",
    long_description=readme,
    author="Ricardo Cabral",
    author_email='ricardo.arturo.cabral@gmail.com',
    url='https://github.com/Cameri/topic_plugin',
    packages=[
        'topic_plugin',
    ],
    package_dir={'topic_plugin':
                 'topic_plugin'},
    include_package_data=True,
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='topic_plugin',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    dependency_links=[
        'git+ssh://git@github.com:BotDevGroup/marvin.git#egg=marvinbot',
    ],
)
