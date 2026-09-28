from __future__ import annotations

import hashlib
import importlib
import importlib.util
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType


@lru_cache(maxsize=None)
def load_protocol(build: int, local: bool = False) -> ModuleType:
    if type(build) is not int or not 0 < build < 2**32:
        raise ValueError('Protocol build must be a positive 32-bit integer')
    if local:
        return importlib.import_module(f'protocol{build}')
    package = importlib.import_module('heroprotocol')
    candidates = [Path(root) / 'versions' / f'protocol{build}.py' for root in package.__path__]
    paths = [path.resolve() for path in candidates if path.is_file()]
    if len(paths) != 1:
        raise ModuleNotFoundError(f'Exactly one official protocol{build}.py is required; found {len(paths)}')
    path = paths[0]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    name = f'_hots_protocol_{build}_{digest}'
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Cannot load protocol {build}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        required = ('typeinfos', 'game_event_types', 'message_event_types', 'tracker_event_types',
                    'replay_header_typeid', 'replay_initdata_typeid', 'game_details_typeid')
        for key in required:
            if not hasattr(module, key):
                raise ImportError(f'Protocol {build} lacks {key}')
        module.recovery_schema_build = build
        module.recovery_schema_sha256 = digest
        return module
    except BaseException:
        sys.modules.pop(name, None)
        raise
