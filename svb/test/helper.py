import datetime
import os
import random
import string
import sys
import unittest2

from mock import patch, Mock

import svb

NOW = datetime.datetime.now()


DUMMY_RECIPIENT = {
    'name': 'John Doe',
    'type': 'individual'
}

DUMMY_TRANSFER = {
    'amount': 400,
    'currency': 'usd',
    'recipient': 'self'
}

SAMPLE_INVOICE = svb.util.json.loads("""
{
  "amount_due": 1305,
  "attempt_count": 0,
  "attempted": true,
  "charge": "ch_wajkQ5aDTzFs5v",
  "closed": true,
  "customer": "cus_osllUe2f1BzrRT",
  "date": 1338238728,
  "discount": null,
  "ending_balance": 0,
  "id": "in_t9mHb2hpK7mml1",
  "livemode": false,
  "next_payment_attempt": null,
  "object": "invoice",
  "paid": true,
  "period_end": 1338238728,
  "period_start": 1338238716,
  "starting_balance": -8695,
  "subtotal": 10000,
  "total": 10000,
  "lines": {
    "invoiceitems": [],
    "prorations": [],
    "subscriptions": [
      {
        "plan": {
          "interval": "month",
          "object": "plan",
          "identifier": "expensive",
          "currency": "usd",
          "livemode": false,
          "amount": 10000,
          "name": "Expensive Plan",
          "trial_period_days": null,
          "id": "expensive"
        },
        "period": {
          "end": 1340917128,
          "start": 1338238728
        },
        "amount": 10000
      }
    ]
  }
}
""")


class SvbTestCase(unittest2.TestCase):
    RESTORE_ATTRIBUTES = ('api_version', 'api_key', 'client_id')

    def setUp(self):
        super(SvbTestCase, self).setUp()

        self._svb_original_attributes = {}

        for attr in self.RESTORE_ATTRIBUTES:
            self._svb_original_attributes[attr] = getattr(svb, attr)

        api_base = os.environ.get('SVB_API_BASE')
        if api_base:
            svb.api_base = api_base
        svb.api_key = os.environ.get(
            'SVB_API_KEY', 'tGN0bIwXnHdwOa85VABjPdSn8nWY7G7I')
        svb.api_version = os.environ.get(
            'SVB_API_VERSION', '2017-04-06')

    def tearDown(self):
        super(SvbTestCase, self).tearDown()

        for attr in self.RESTORE_ATTRIBUTES:
            setattr(svb, attr, self._svb_original_attributes[attr])


class SvbUnitTestCase(SvbTestCase):
    REQUEST_LIBRARIES = ['urlfetch', 'requests', 'pycurl']

    if sys.version_info >= (3, 0):
        REQUEST_LIBRARIES.append('urllib.request')
    else:
        REQUEST_LIBRARIES.append('urllib2')

    def setUp(self):
        super(SvbUnitTestCase, self).setUp()

        self.request_patchers = {}
        self.request_mocks = {}
        for lib in self.REQUEST_LIBRARIES:
            patcher = patch("svb.http_client.%s" % (lib,))

            self.request_mocks[lib] = patcher.start()
            self.request_patchers[lib] = patcher

    def tearDown(self):
        super(SvbUnitTestCase, self).tearDown()

        for patcher in self.request_patchers.itervalues():
            patcher.stop()


class SvbApiTestCase(SvbTestCase):

    def setUp(self):
        super(SvbApiTestCase, self).setUp()

        self.requestor_patcher = patch('svb.api_requestor.APIRequestor')
        requestor_class_mock = self.requestor_patcher.start()
        self.requestor_mock = requestor_class_mock.return_value

    def tearDown(self):
        super(SvbApiTestCase, self).tearDown()

        self.requestor_patcher.stop()

    def mock_response(self, res):
        self.requestor_mock.request = Mock(return_value=(res, 'reskey'))


class SvbResourceTest(SvbApiTestCase):

    def setUp(self):
        super(SvbResourceTest, self).setUp()
        self.mock_response({})


class MyResource(svb.resource.APIResource):
    pass


class MySingleton(svb.resource.SingletonAPIResource):
    pass


class MyListable(svb.resource.ListableAPIResource):
    pass


class MyCreatable(svb.resource.CreateableAPIResource):
    pass


class MyUpdateable(svb.resource.UpdateableAPIResource):
    pass


class MyDeletable(svb.resource.DeletableAPIResource):
    pass


class MyComposite(svb.resource.ListableAPIResource,
                  svb.resource.CreateableAPIResource,
                  svb.resource.UpdateableAPIResource,
                  svb.resource.DeletableAPIResource):
    pass
