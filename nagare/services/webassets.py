# --
# Copyright (c) 2008-2022 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

from __future__ import absolute_import

import gzip
from collections import defaultdict

from nagare.services import plugin
from nagare.server import reference
from nagare.admin.webassets import Command
from webassets import Environment, filter, Bundle
from webassets.bundle import get_all_bundle_files
from dukpy.webassets import TypeScript, BabelJSX, BabelJS, CompileLess


class GZipFilter(filter.Filter):
    name = 'gzip'
    binary_output = True

    def output(self, _in, out, **kw):
        gzip.GzipFile(fileobj=out, mode='wb').write(_in.read().encode('utf-8'))


class Storage(Environment.config_storage_class):
    def items(self):
        return self._dict.items()


class Env(Environment):
    config_storage_class = Storage

    def copy(self, **config):
        config = dict(self.config.items(), **config)
        return self.__class__(**config)


def on_change(event, path, o, method, bundles):
    return (event.event_type in ('created', 'modified')) and getattr(o, method)(path, bundles)


class WebAssets(plugin.Plugin):
    """Web assets manager
    """
    CONFIG_SPEC = dict(
        plugin.Plugin.CONFIG_SPEC,
        bundles='string(default=None)',
        output_dir='string(default="$static")',
        watch='boolean(default=False)',
        reload='boolean(default=False)',
        refresh='boolean(default=False)',

        debug='boolean(default=False)',
        cache='boolean(default=True)',
        url_expire='boolean(default=None)',
        manifest='string(default="$static/manifest.json")',
        manifest_cache='boolean(default=True)',
        versions='string(default="hash")',
        updater='string(default="timestamp")',
        load_path='string_list(default=list("$root"))',
        cache_file_mode='string(default=None)',

        mapping={'___many___': 'string'}
    )

    def __init__(
            self,
            name, dist,
            bundles=None, output_dir=None,
            watch=False, reload=False, refresh=False, manifest='',
            mapping=None,
            reloader_service=None, services_service=None,
            **config
    ):
        """Initialization
        """
        services_service(
            super(WebAssets, self).__init__, name, dist,
            bundles=bundles, output_dir=output_dir,
            watch=watch, reload=reload, refresh=refresh, manifest=manifest,
            mapping=mapping,
            **config
        )

        manifest = 'json:{}'.format(manifest) if manifest else None
        self.environment = Env(
            directory=output_dir,
            auto_build=False,
            manifest=manifest,
            url_mapping=mapping or {},
            **config
        )
        self.reload = reload
        self.refresh = refresh
        self.reloader = reloader_service if watch else None

        filter.register_filter(TypeScript)
        filter.register_filter(BabelJSX)
        filter.register_filter(BabelJS)
        filter.register_filter(CompileLess)
        filter.register_filter(GZipFilter)

        if bundles:
            bundles = reference.load_object(bundles)[0]
            if callable(bundles):
                bundles = services_service(bundles, self)

            for name, bundle in bundles.items():
                self.environment.register(name, bundle)
                bundle.get_version()

        self.bundles = bundles

    @property
    def config(self):
        return self.environment.config

    def build_on_change(self, path, bundles):
        status = Command('build').run(self, bundles=bundles)
        if status == 0:
            self.logger.info('Build done: ' + ', '.join(bundles))

        return self.reload

    def handle_start(self, app, services_service, reloader_service=None):
        self.environment.config.setdefault('url', app.static_url)

        if self.bundles and (reloader_service is not None):
            filenames = defaultdict(tuple)
            for bundle_name, bundle in self.bundles.items():
                for filename in set(get_all_bundle_files(bundle)):
                    filenames[filename] += (bundle_name,)

            bundles = {bundles: bundles for bundles in filenames.values()}

            for filename, bundle_names in filenames.items():
                reloader_service.watch_file(
                    filename,
                    on_change, o=self, method='build_on_change', bundles=bundles[bundle_names]
                )

    def urls(self):
        environment = self.environment.copy(cache=False, auto_build=self.refresh)
        bundles = {
            bundle_name: Bundle(output=bundle.output, version=bundle.version, env=environment)
            for bundle_name, bundle
            in self.bundles.items()
        }

        def _(*bundle_names):
            selected_bundles = [bundles[bundle_name] for bundle_name in (bundle_names or bundles)]

            return sum([bundle.urls() for bundle in selected_bundles], [])

        return _
