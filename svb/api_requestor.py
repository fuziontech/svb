import calendar
import datetime
import platform
import time
import urllib
import urlparse
import warnings

import svb
from svb import error, http_client, version, util
from svb.multipart_data_generator import MultipartDataGenerator


def _encode_datetime(dttime):
    if dttime.tzinfo and dttime.tzinfo.utcoffset(dttime) is not None:
        utc_timestamp = calendar.timegm(dttime.utctimetuple())
    else:
        utc_timestamp = time.mktime(dttime.timetuple())

    return int(utc_timestamp)


def _encode_nested_dict(key, data, fmt='%s[%s]'):
    d = {}
    for subkey, subvalue in data.iteritems():
        d[fmt % (key, subkey)] = subvalue
    return d


def _api_encode(data):
    for key, value in data.iteritems():
        key = util.utf8(key)
        if value is None:
            continue
        elif hasattr(value, 'svb_id'):
            yield (key, value.svb_id)
        elif isinstance(value, list) or isinstance(value, tuple):
            for sv in value:
                if isinstance(sv, dict):
                    subdict = _encode_nested_dict(key, sv, fmt='%s[][%s]')
                    for k, v in _api_encode(subdict):
                        yield (k, v)
                else:
                    yield ("%s[]" % (key,), util.utf8(sv))
        elif isinstance(value, dict):
            subdict = _encode_nested_dict(key, value)
            for subkey, subvalue in _api_encode(subdict):
                yield (subkey, subvalue)
        elif isinstance(value, datetime.datetime):
            yield (key, _encode_datetime(value))
        else:
            yield (key, util.utf8(value))


def _build_api_url(url, query):
    scheme, netloc, path, base_query, fragment = urlparse.urlsplit(url)

    if base_query:
        query = '%s&%s' % (base_query, query)

    return urlparse.urlunsplit((scheme, netloc, path, query, fragment))


class APIRequestor(object):

    def __init__(self, key=None, client=None, api_base=None, api_version=None,
                 account=None):
        self.api_base = api_base or svb.api_base
        self.api_key = key
        self.api_version = api_version or svb.api_version
        self.svb_account = account

        from svb import verify_ssl_certs as verify
        from svb import proxy

        self._client = client or svb.default_http_client or \
            http_client.new_default_http_client(
                verify_ssl_certs=verify, proxy=proxy)

    @classmethod
    def format_app_info(cls, info):
        str = info['name']
        if info['version']:
            str += "/%s" % (info['version'],)
        if info['url']:
            str += " (%s)" % (info['url'],)
        return str

    def request(self, method, url, params=None, headers=None):
        rbody, rcode, rheaders, my_api_key = self.request_raw(
            method.lower(), url, params, headers)
        resp = self.interpret_response(rbody, rcode, rheaders)
        return resp, my_api_key

    def handle_error_response(self, rbody, rcode, resp, rheaders):
        try:
            error_data = resp['error']
        except (KeyError, TypeError):
            raise error.APIError(
                "Invalid response object from API: %r (HTTP response code "
                "was %d)" % (rbody, rcode),
                rbody, rcode, resp)

        err = self.specific_api_error(
            rbody, rcode, resp, rheaders, error_data)
        raise err

    def specific_api_error(self, rbody, rcode, resp, rheaders, error_data):
        util.log_info(
            'SVB API error received',
            error_code=error_data.get('code'),
            error_type=error_data.get('type'),
            error_message=error_data.get('message'),
            error_param=error_data.get('param'),
        )

        # Rate limits were previously coded as 400's with code 'rate_limit'
        if rcode == 429 or (rcode == 400 and
                            error_data.get('code') == 'rate_limit'):
            return error.RateLimitError(
                error_data.get('message'), rbody, rcode, resp, rheaders)
        elif rcode in [400, 404]:
            return error.InvalidRequestError(
                error_data.get('message'), error_data.get('param'),
                rbody, rcode, resp, rheaders)
        elif rcode == 401:
            return error.AuthenticationError(
                error_data.get('message'), rbody, rcode, resp, rheaders)
        elif rcode == 402:
            return error.CardError(
                error_data.get('message'), error_data.get('param'),
                error_data.get('code'), rbody, rcode, resp, rheaders)
        elif rcode == 403:
            return error.PermissionError(
                error_data.get('message'), rbody, rcode, resp, rheaders)
        else:
            return error.APIError(
                error_data.get('message'), rbody, rcode, resp, rheaders)

    def request_headers(self, api_key, method):
        user_agent = 'SVB/v1 PythonBindings/%s' % (version.VERSION,)
        if svb.app_info:
            user_agent += " " + self.format_app_info(svb.app_info)

        ua = {
            'bindings_version': version.VERSION,
            'lang': 'python',
            'publisher': 'svb',
            'httplib': self._client.name,
        }
        for attr, func in [['lang_version', platform.python_version],
                           ['platform', platform.platform],
                           ['uname', lambda: ' '.join(platform.uname())]]:
            try:
                val = func()
            except Exception as e:
                val = "!! %s" % (e,)
            ua[attr] = val
        if svb.app_info:
            ua['application'] = svb.app_info

        headers = {
            'X-SVB-Client-User-Agent': util.json.dumps(ua),
            'User-Agent': user_agent,
            'Authorization': 'Bearer %s' % (api_key,),
        }

        if self.svb_account:
            headers['SVB-Account'] = self.svb_account

        if method == 'post':
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

        if self.api_version is not None:
            headers['Svb-Version'] = self.api_version

        return headers

    def request_raw(self, method, url, params=None, supplied_headers=None):
        """
        Mechanism for issuing an API call
        """

        if self.api_key:
            my_api_key = self.api_key
        else:
            from svb import api_key
            my_api_key = api_key

        if my_api_key is None:
            raise error.AuthenticationError(
                'No API key provided. (HINT: set your API key using '
                '"svb.api_key = <API-KEY>"). You can generate API keys '
                'from the SVB web portal.  See https://docs.svbplatform.com'
                'for details, or email support@svb.com if you have any '
                'questions.')

        abs_url = '%s%s' % (self.api_base, url)

        encoded_params = urllib.urlencode(list(_api_encode(params or {})))

        if method == 'get' or method == 'delete':
            if params:
                abs_url = _build_api_url(abs_url, encoded_params)
            post_data = None
        elif method == 'post':
            if supplied_headers is not None and \
                    supplied_headers.get("Content-Type") == \
                    "multipart/form-data":
                generator = MultipartDataGenerator()
                generator.add_params(params or {})
                post_data = generator.get_post_data()
                supplied_headers["Content-Type"] = \
                    "multipart/form-data; boundary=%s" % (generator.boundary,)
            else:
                post_data = encoded_params
        else:
            raise error.APIConnectionError(
                'Unrecognized HTTP method %r.  This may indicate a bug in the '
                'SVB bindings.  Please contact support@svb.com for '
                'assistance.' % (method,))

        headers = self.request_headers(my_api_key, method)

        if supplied_headers is not None:
            for key, value in supplied_headers.items():
                headers[key] = value

        util.log_info('Request to SVB api', method=method, path=abs_url)
        util.log_debug(
            'Post details', post_data=post_data, api_version=self.api_version)

        rbody, rcode, rheaders = self._client.request(
            method, abs_url, headers, post_data)

        util.log_info(
            'SVB API response', path=abs_url, response_code=rcode)
        util.log_debug('API response body', body=rbody)
        if 'Request-Id' in rheaders:
            util.log_debug('Dashboard link for request',
                           link=rheaders['Request-Id'])
        return rbody, rcode, rheaders, my_api_key

    def interpret_response(self, rbody, rcode, rheaders):
        try:
            if hasattr(rbody, 'decode'):
                rbody = rbody.decode('utf-8')
            resp = util.json.loads(rbody)
        except Exception:
            raise error.APIError(
                "Invalid response body from API: %s "
                "(HTTP response code was %d)" % (rbody, rcode),
                rbody, rcode, rheaders)
        if not (200 <= rcode < 300):
            self.handle_error_response(rbody, rcode, resp, rheaders)
        return resp
