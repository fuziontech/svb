import datetime
import hmac
import json
import sys
import urllib 

import requests


def _encode_datetime(dttime):
    if dttime.tzinfo and dttime.tzinfo.utcoffset(dttime) is not None:
        utc_timestamp = calendar.timegm(dttime.utctimetuple())
    else:
        utc_timestamp = time.mktime(dttime.timetuple())

    return int(utc_timestamp)


def _urlencode(self, query):
    if sys.version_info.major == 3:
        return urllib.parse.urlencode(query)
    else:
        return urllib.urlencode(query)


class APIRequestor(object):
    """
    Connection object managing requests to bank
    """

    methods = frozenset(["GET", "DELETE", "POST", "PATCH"])

    def __init__(self, key, hmac_secret, base_url='https://api.svb.com'):
        self.key = key
        self.hmac_secret = hmac_secret
        self.base_url = base_url


    def _hmac_sign(self, timestamp, method, path, query, body):
        message = "\n".join([timestamp, method, path, query, body])
        signer = hmac.new(self.hmac_secret)
        signer.update(message)
        return signer.hexdigest()

    def _headers(self, method, path, query="", body=""):
        timestamp = datetime.datetime.now()
        assert method in self.methods, "Method not valid"
        hmac_signature = self._hmac_sign(timestamp, method, path, query, body)
        headers = {
            "X-Timestamp": timestamp,
            "X-Signature": hmac_signature,
            "Authorization": "Bearer" + self.key,
            "Content-Type": "application/json",
        }
        return headers

    def delete(self, path):
        method = 'DELETE'
        r = requests.delete(path, headers=self._headers(method, path))
        return r

    def get(self, path, query={}):
        method = 'GET'
        squery = self._urlencode(query)
        headers = self._headers(method, path, squery)
        r = requests.get(path, params=query, headers=headers)
        return r

    def patch(self, path, data):
        method = 'PATCH'
        sdata = json.dumps({"data": data})
        headers = self._headers(method, path, body=sdata)
        r = requests.patch(path, headers=headers, data=sdata)
        return r

    def post(self, path, data):
        method = 'POST'
        sdata = json.dumps({"data": data})
        headers = self._headers(method, path, body=sdata)
        r = requests.post(path, headers=headers, data=sdata)
        return r

    def upload(self, path, filesrc, mimetype):
        timestamp = datetime.datetime.now()
        method = 'POST'
        headers = self._headers(method, path)
        r = requests.post(path, headers=headers, files=filesrc)
        return r

class ACH
