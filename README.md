# SVB Python Library

The SVB Python library provides convenient access to the SVB Bank
platform API from applications written in the Python language.

## Documentation

See the [API docs](http://docs.svbplatform.com/).

## Installation

You don't need this source code unless you want to modify the package. If you just
want to use the package, just run:

    pip install --upgrade svb

or

    easy_install --upgrade svb

Install from source with:

    python setup.py install

### Requirements

* Python 2.6+ or Python 3.3+ (PyPy supported)

## Usage

The library needs to be configured with your account's secret key which
you can get by contacting us. Set `svb.api_key` to its value:

``` python
import svb
svb.api_key = "test_..."

# list ACH transactions
svb.ACH.list()

# retrieve single ACH transaction
svb.ACH.retrieve("1234321")
```

### Per-request Configuration

For apps that need to use multiple keys during the lifetime of a process,
it's also possible to set a per-request key and/or account:

``` python
import svb

# list ACH transactions
svb.ACH.list(
    api_key="test_...",
)

# retrieve single ACH transaction
svb.ACH.retrieve(
    "1234321",
    api_key="test_...",
)
```

### Configuring a Client

The library can be configured to use `urlfetch`, `requests`, `pycurl`, or
`urllib2` with `svb.default_http_client`:

``` python
client = svb.http_client.UrlFetchClient()
client = svb.http_client.RequestsClient()
client = svb.http_client.PycurlClient()
client = svb.http_client.Urllib2Client()
svb.default_http_client = client
```

Without a configured client, by default the library will attempt to load
libraries in the order above (i.e. `urlfetch` is preferred with `urllib2` used
as a last resort). We usually recommend that people use `requests` for security.

### Configuring a Proxy

A proxy can be configured with `svb.proxy`:

``` python
svb.proxy = "https://user:pass@example.com:1234"
```

### Logging

The library can be configured to emit logging that will give you better insight
into what it's doing. The `info` logging level is usually most appropriate for
production use, but `debug` is also available for more verbosity.

There are a few options for enabling it:

1. Set the environment variable `SVB_LOG` to the value `debug` or `info`
   ```
   $ export SVB_LOG=debug
   ```

2. Set `svb.log`:
   ```py
   import svb
   svb.log = 'debug'
   ```

3. Enable it through Python's logging module:
   ```py
   import logging
   logging.basicConfig()
   logging.getLogger('svb').setLevel(logging.DEBUG)
   ```

### Writing a Plugin

If you're writing a plugin that uses the library, we'd appreciate it if you
identified using `svb.set_app_info()`:

   ```py
   svb.set_app_info("MyAwesomePlugin", version="1.2.34", url="https://myawesomeplugin.info")
   ```

This information is passed along when the library makes calls to the SVB API.

<!--
# vim: set tw=79:
-->
