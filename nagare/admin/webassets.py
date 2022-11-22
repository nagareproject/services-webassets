# --
# Copyright (c) 2008-2022 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

from __future__ import absolute_import

import sys
from os import path
sys.path.insert(0, path.join(path.dirname(__file__), '..', 'vendor'))


from webassets import script  # noqa: E402
from nagare.admin import command  # noqa: E402


class Commands(command.Commands):
    DESC = 'static assets generation subcommands'


class Command(command.Command):

    def run(self, webassets_service, **config):
        runner = script.CommandLineEnvironment(webassets_service.environment, webassets_service.logger)

        try:
            runner.invoke(self.name, config)
            return 0
        except (script.BuildError, script.CommandError) as e:
            print(e.args[0])
            return 1


class Build(Command):
    DESC = 'build assets'

    def set_arguments(self, parser):
        super(Build, self).set_arguments(parser)

        parser.add_argument(
            '--no-cache', action='store_true',
            help='do not use a cache that might be configured'
        )

        parser.add_argument(
            '-b', '--bundle', dest='bundles', action='append',
            help='optional bundle names to process. If none are specified, then all known bundles will be built'
        )

    def run(self, webassets_service, services_service, no_cache=False, bundles=()):
        bundles = bundles or list(webassets_service.bundles)

        return services_service(super(Build, self).run, no_cache=no_cache, bundles=bundles)


class Clean(Command):
    DESC = 'delete generated assets'


class Check(Command):
    DESC = 'check if assets need to be rebuilt'


class List(command.Command):
    DESC = 'list assets'

    def run(self, webassets_service):
        for bundle in webassets_service.bundles:
            print(bundle)

        return 0
