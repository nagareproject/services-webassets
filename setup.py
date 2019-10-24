# Encoding: utf-8

# --
# Copyright (c) 2008-2019 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

from os import path

from setuptools import setup, find_packages


here = path.normpath(path.dirname(__file__))

with open(path.join(here, 'README.rst')) as long_description:
    LONG_DESCRIPTION = long_description.read()

setup(
    name='nagare-services-webassets',
    author='Net-ng',
    author_email='alain.poirier@net-ng.com',
    description='Web assets service',
    long_description=LONG_DESCRIPTION,
    license='BSD',
    keywords='',
    url='https://github.com/nagareproject/services-webassets',
    packages=find_packages(),
    zip_safe=False,
    setup_requires=['setuptools_scm'],
    use_scm_version=True,
    install_requires=['glob2', 'dukpy', 'webassets', 'nagare-server'],
    entry_points='''
        [nagare.commands]
        webassets = nagare.admin.webassets:Commands

        [nagare.commands.webassets]
        build = nagare.admin.webassets:Build
        clean = nagare.admin.webassets:Clean
        check = nagare.admin.webassets:Check

        [nagare.services]
        webassets = nagare.services.webassets:WebAssets
    '''
)
