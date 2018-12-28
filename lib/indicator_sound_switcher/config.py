"""
Configuration backend implementation.
"""
import logging
import os.path
import json


class Config(dict):
    """Extension of the standard dict class that overrides item getter to add default value support and sub-dictionary
    autocreation.
    """

    @staticmethod
    def load_from_file(file_name: str):
        """Load, parse and return JSON configuration from a file specified by name.
        :param file_name: Name of the JSON configuration file.
        :returns An instance of Config (empty if the file doesn't exist).
        """
        # Check if the file exists
        if not os.path.isfile(file_name):
            logging.info('Configuration file %s not found, falling back to defaults', file_name)
            return Config()

        # Open and read in the file
        with open(file_name, 'r') as cf:
            # Create instances of Config instead of dict
            conf = json.load(cf, object_hook=lambda dct: Config(dct))
        logging.info('Loaded configuration file %s', file_name)
        return conf

    def save_to_file(self, file_name: str):
        """Save configuration to the given JSON file.
        :param file_name: Name of the JSON configuration file to save the configuration to.
        """
        with open(file_name, 'w') as cf:
            json.dump(self, cf, indent=4, ensure_ascii=False)

    # noinspection PyMissingConstructor
    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def __getitem__(self, key: [str, tuple]):
        """Override the inherited getter.
        :param key Either a key name (string) or a tuple consisting of
          [0] Configuration key name and
          [1] Optional default value to return if the key isn't found. If not given, a new, empty Config instance will
              be inserted and returned
        :rtype : V
        :return Configuration value corresponfing to the name or the default.
        """
        # Sort the arguments
        default = None
        default_given = False
        if type(key) is tuple:
            key_name = key[0]
            if len(key) > 1:
                default = key[1]
                default_given = True
        # If key is not a tuple, consider it a scalar [string] key name
        else:
            key_name = key

        # Try to fetch a key
        if key_name in self:
            return dict.__getitem__(self, key_name)

        # We don't have the key. If a default was given, return it
        if default_given:
            return default

        # Insert an empty Config instance and return it
        result = Config()
        dict.__setitem__(self, key_name, result)
        return result

    def __setitem__(self, key, value):
        """Override the inherited setter to convert incoming dict values into Config instances and to remove values when
        they are assigned None.
        """
        # A value of None means removing it
        if value is None:
            dict.__delitem__(self, key)

        else:
            # Convert dictionaries into Config instances
            if type(value) is dict:
                value = Config(value)
            dict.__setitem__(self, key, value)

    def update(self, *args, **kwargs):
        """Override to provide proper setter calls, also for the constructor."""
        # Process positional arguments (a single iterable is allowed)
        if args:
            if len(args) > 1:
                raise TypeError('update() expected at most 1 arguments, got {}'.format(len(args)))
            for k, v in dict(args[0]).items():
                self[k] = v

        # Process keyword arguments
        for k, v in kwargs.items():
            self[k] = v
