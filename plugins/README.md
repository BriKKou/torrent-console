# plugins/

Put your own providers here, one module per provider: `<key>.py`, defining a `Provider` subclass whose `key` is `<key>`. They are loaded exactly like the ones in `app/providers/` and enabled the same way, under `providers` in `config.json`.

Everything in this folder except this file is ignored by git, so a provider that holds site-specific code stays on your machine. See "Adding a provider" in the main README.
