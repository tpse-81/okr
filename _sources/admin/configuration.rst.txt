Configuration
-------------
All configuration options can either be configured by changing `config.toml` or setting the respective environment variable. Environment variables have higher priority than the configuration file.

- For example, you can set the database url by either setting the ``OKR_DATABASE_URL`` environment variable or by changing ``database_url`` in the ``okr`` section of the config.

Below is an example configuration file:

.. literalinclude :: ../../examples/config.toml
   :language: toml
   :caption: ``config.toml``

The minimum changes you have to do are the following:

1. Change `cors_allow_origins` in `okr` to include the url of your frontend (e.g. *https://okr.example.com*)
2. Change the `secret` in `okr.jwt_config` to a randomly generated sequence of characters
3. Change the admin password by setting `password_hash` to the output of ``./maintenance_script.py hash-password "<your-password-here>"``

For further information about the configuration, please see the detailed documentation at :doc:`../api/config`.
