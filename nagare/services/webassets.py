# --
# Copyright (c) 2008-2020 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

from __future__ import absolute_import

from nagare.services import plugin
from nagare.server import reference
from nagare.admin.webassets import Command
from webassets import Environment, filter, Bundle
from webassets.bundle import get_all_bundle_files
from dukpy.webassets import TypeScript, BabelJSX, BabelJS


class Storage(Environment.config_storage_class):
    def items(self):
        return self._dict.items()


class Env(Environment):
    config_storage_class = Storage

    def copy(self, **config):
        config = dict(self.config.items(), **config)
        return self.__class__(**config)


def on_change(event, path, o, method, bundle):
    return (event.event_type in ('created', 'modified')) and getattr(o, method)(path, bundle)


class WebAssets(plugin.Plugin):
    """Web assets manager
    """
    CONFIG_SPEC = {
        'bundles': 'string(default=None)',
        'output_dir': 'string(default=$static)',
        'watch': 'boolean(default=False)',
        'reload': 'boolean(default=False)',
        'refresh': 'boolean(default=False)',

        'debug': 'boolean(default=False)',
        'cache': 'boolean(default=True)',
        'url_expire': 'boolean(default=None)',
        'manifest': 'string(default=$static/manifest.json)',
        'manifest_cache': 'boolean(default=True)',
        'versions': 'string(default="hash")',
        'updater': 'string(default="timestamp")',
        'load_path': 'force_list(default=list($root))',
        'cache_file_mode': 'string(default=None)',

        'mapping': {'__many__': 'string'}
    }

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

        if bundles:
            bundles = reference.load_object(bundles)[0]
            if callable(bundles):
                bundles = services_service(bundles, self)

            for name, bundle in bundles.items():
                self.environment.register(name, bundle)
                bundle.get_version()

        self.bundles = bundles

    def build_on_change(self, path, bundle):
        status = Command('build').run(self, bundles=[bundle])
        if status == 0:
            print('Build done')

        return self.reload

    def handle_start(self, app, services_service, reloader_service=None):
        self.environment.config.setdefault('url', app.static_url)

        if self.bundles and (reloader_service is not None):
            for name, bundle in self.bundles.items():
                for filename in set(get_all_bundle_files(bundle)):
                    reloader_service.watch_file(
                        filename,
                        on_change, o=self, method='build_on_change', bundle=name
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
