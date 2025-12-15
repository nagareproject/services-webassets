# --
# Copyright (c) 2014-2025 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

import os
import sys
import gzip
from collections import defaultdict

vendor_path = os.path.join(os.path.dirname(__file__), '..', 'vendor')
if vendor_path not in sys.path:
    sys.path.insert(0, vendor_path)

from webassets import Bundle, Environment, filter  # noqa: F401
from dukpy.webassets import BabelJS, BabelJSX, TypeScript, CompileLess
from webassets.bundle import get_all_bundle_files

from nagare.server import reference
from nagare.services import plugin
from nagare.admin.webassets import Command


class GZipFilter(filter.Filter):
    name = 'gzip'
    binary_output = True

    def output(self, _in, out, **kw):
        try:
            output_file = gzip.GzipFile(fileobj=out, mode='wb')
            output_file.write(_in.read().encode('utf-8'))
        finally:
            output_file.close()


class Storage(Environment.config_storage_class):
    def items(self):
        return self._dict.items()


class Env(Environment):
    config_storage_class = Storage

    def copy(self, **config):
        config = dict(self.config.items(), **config)
        return self.__class__(**config)


def on_change(event, path, o, method, bundles):
    return getattr(o, method)(path, bundles) if event.event_type in ('created', 'modified') else None


class WebAssets(plugin.Plugin):
    """Web assets manager."""

    CONFIG_SPEC = plugin.Plugin.CONFIG_SPEC | {
        'bundles': 'string(default=None)',
        'output_dir': 'string(default="$static")',
        'watch': 'boolean(default=True)',
        'reload': 'boolean(default=False)',
        'debug': 'boolean(default=False)',
        'cache': 'boolean(default=True)',
        'url': 'string(default="/static$app_url")',
        'url_expire': 'boolean(default=None)',
        'manifest': 'string(default="$static/manifest.json")',
        'manifest_cache': 'boolean(default=True)',
        'versions': 'string(default="hash")',
        'load_path': 'string_list(default=list("$root"))',
        'cache_file_mode': 'string(default=None)',
        'mapping': {'___many___': 'string'},
    }

    def __init__(
        self,
        name,
        dist,
        bundles=None,
        output_dir=None,
        watch=True,
        reload=False,
        manifest='',
        mapping=None,
        services_service=None,
        **config,
    ):
        """Initialization."""
        services_service(
            super().__init__,
            name,
            dist,
            bundles=bundles,
            output_dir=output_dir,
            watch=watch,
            reload=reload,
            manifest=manifest,
            mapping=mapping,
            **config,
        )

        self.environment = Env(
            directory=output_dir,
            auto_build=False,
            manifest='json:{}'.format(manifest) if manifest else False,
            url_mapping=mapping or {},
            **config,
        )
        self.reload = False if reload else None
        self.watch = watch

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

        self.bundles = bundles or {}

    @property
    def config(self):
        return self.environment.config

    def build_on_change(self, path, bundles):
        status = Command('build').run(self, bundles=bundles)
        if status == 0:
            self.logger.info('Build done: ' + ', '.join(bundles))

        return self.reload

    def handle_serve(self, app, services_service, reloader_service=None):
        self.environment.config.setdefault('url', app.static_url)

        if self.watch and (reloader_service is not None) and self.bundles:
            filenames = defaultdict(tuple)
            for bundle_name, bundle in self.bundles.items():
                for filename in set(get_all_bundle_files(bundle)):
                    filenames[filename] += (bundle_name,)

            bundles = {bundles: bundles for bundles in filenames.values()}

            for filename, bundle_names in filenames.items():
                reloader_service.watch_file(
                    filename, on_change, o=self, method='build_on_change', bundles=bundles[bundle_names]
                )

    def urls(self, *bundles_names):
        return {bundle_name: self.bundles[bundle_name].urls() for bundle_name in bundles_names or self.bundles}
