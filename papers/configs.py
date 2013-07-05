import os
from .p3 import configparser

# constant stuff (DFT = DEFAULT)

MAIN_SECTION = 'papers'
DFT_CONFIG_PATH = os.path.expanduser('~/.papersrc')
try:
    DFT_EDIT_CMD = os.environ['EDITOR']
except KeyError:
    DFT_EDIT_CMD = 'vi'

DFT_PLUGINS = ''

DFT_CONFIG = {'papers_dir'  : os.path.expanduser('~/.papers'),
              'doc_dir'     : 'doc',
              'import_copy' : True,
              'import_move' : False,
              'color'       : True,
              'version'     : 3,
              'version_warning' : True,

              'open_cmd'    : 'open',
              'edit_cmd'    : DFT_EDIT_CMD,
              'plugins'     : DFT_PLUGINS
             }

BOOLEANS = {'import_copy', 'import_move', 'color', 'version_warning'}


# package-shared config that can be accessed using :
# from configs import config
_config = None


def config(section=MAIN_SECTION):
    if _config is None:
        raise ValueError('not config instanciated yet')
    _config._section = section
    return _config


class Config(object):

    def __init__(self, **kwargs):
        object.__setattr__(self, '_section', MAIN_SECTION)  # active section
        object.__setattr__(self, '_cfg', configparser.SafeConfigParser())

        self._cfg.add_section(self._section)
        for name, value in DFT_CONFIG.items():
            self._cfg.set(self._section, name, str(value))

        for name, value in kwargs.items():
            self.__setattr__(name, value)

    def as_global(self):
        global _config
        _config = self

    def load(self, path=DFT_CONFIG_PATH):
        self._cfg.read(path)
        return self

    def save(self, path=DFT_CONFIG_PATH):
        with open(path, 'w') as f:
            self._cfg.write(f)

    def __setattr__(self, name, value):
        if name in ('_cfg', '_section'):
            object.__setattr__(self, name, value)
        else:
            if type(value) is bool:
                BOOLEANS.add(name)
            self._cfg.set(self._section, name, str(value))

    def __getattr__(self, name):
        value = self._cfg.get(self._section, name)
        if name in BOOLEANS:
            value = str2bool(value)
        return value

    def get(self, name, default=None):
        try:
            return self.__getattr__(name)
        except (configparser.NoOptionError, configparser.NoSectionError):
            return default

    def items(self):
        for name, value in self._cfg.items(self._section):
            if name in BOOLEANS:
                value = str2bool(value)
            yield name, value


def str2bool(s):
    return str(s).lower() in ('yes', 'true', 't', 'y', '1')
