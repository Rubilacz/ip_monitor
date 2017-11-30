# -*- coding: utf-8 -*-

import configparser

class ConfigStore:

    def __init__(self, config_file):
        self._config_file = config_file
        self._config_parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        self._config_parser.read(config_file)

    def get(self, section, option, default_value=None):
        try:
            value = self._config_parser[section][option]
            return default_value if not value else value
        except KeyError:
            return default_value

    def get_as_int(self, section, option, default_value=0):
        return int(self.get(section, option, default_value))

    def set(self, section, option, value):
        if section not in self._config_parser.sections():
            self._config_parser.add_section(section)
        self._config_parser[section][option] = value
        with open(self._config_file, 'w') as f:
            self._config_parser.write(f)
