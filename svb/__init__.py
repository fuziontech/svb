# SVB Python bindings
# API docs at http://docs.svbplatform.com/
# Author:
# James Greenhill <jgreenhill@svb.com>


# Configuration variables

api_key = None
hmac_key = None
client_id = None
api_base = 'https://api.svb.com'
upload_api_base = 'https://api.svb.com'
api_version = None
verify_ssl_certs = True
proxy = None
default_http_client = None
app_info = None

# Set to either 'debug' or 'info', controls console logging
log = None


# Resource
from svb.resource import (  # noqa
    Account,
    ACH,
    Book,
    VirtualCard,
    Wire,
    # Onboarding
    Company,
    Person,
    Login,
    ParentCompany,
    Address,
    FileUpload,
    Document,
    GovernmentID,
    )

# Error imports.  Note that we may want to move these out of the root
# namespace in the future and you should prefer to access them via
# the fully qualified `svb.error` module.

from svb.error import (  # noqa
    APIConnectionError,
    APIError,
    AuthenticationError,
    PermissionError,
    RateLimitError,
    CardError,
    InvalidRequestError,
    SignatureVerificationError,
    SVBError)

# Sets some basic information about the running application that's sent along
# with API requests. Useful for plugin authors to identify their plugin when
# communicating with SVB.
#
# Takes a name and optional version and plugin URL.
def set_app_info(name, version=None, url=None):
    global app_info
    app_info = {
        'name': name,
        'version': version,
        'url': url,
    }
