
from __future__ import print_function

import sys
from collections import namedtuple

try:
    from unittest import mock
except ImportError:
    import mock

from svb import util
from svb.test.helper import SvbUnitTestCase

import __builtin__

PRINT_FUNC_STRING = __builtin__.__name__ + '.print'

LogTestCase = namedtuple('LogTestCase', 'env flag should_output')
FmtTestCase = namedtuple('FmtTestCase', 'props expected')


class UtilTests(SvbUnitTestCase):
    DUMMY_REQ_ID = 'req_qsxPhqHyLxcoaM'

    def test_test_apikey(self):
        with mock.patch('svb.api_key', 'sk_test_KOWobxXidxNlIx'):
            link = util.dashboard_link(self.DUMMY_REQ_ID)
            self.assertEqual(
                link,
                'http://docs.svbplatform.com/'
            )

    def test_live_apikey(self):
        with mock.patch('svb.api_key', 'sk_live_axwITqZSgTUXSN'):
            link = util.dashboard_link(self.DUMMY_REQ_ID)
            self.assertEqual(
                link,
                'http://docs.svbplatform.com/'
            )

    def test_no_apikey(self):
        with mock.patch('svb.api_key', None):
            link = util.dashboard_link(self.DUMMY_REQ_ID)
            self.assertEqual(
                link,
                'http://docs.svbplatform.com/'
            )

    def test_old_apikey(self):
        with mock.patch('svb.api_key', 'axwITqZSgTUXSN'):
            link = util.dashboard_link(self.DUMMY_REQ_ID)
            self.assertEqual(
                link,
                'http://docs.svbplatform.com/'
            )

    def patch_val(self, var, value):
        patcher = mock.patch(var, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def patch_mock(self, var):
        patcher = mock.patch(var)
        mock_val = patcher.start()
        self.addCleanup(patcher.stop)
        return mock_val

    def log_test_loop(self, test_cases, logging_func, logger_name):
        for case in test_cases:
            with self.subTest(env=case.env, flag=case.flag):
                try:
                    logger_mock = self.patch_mock(logger_name)
                    print_mock = self.patch_mock(PRINT_FUNC_STRING)
                    self.patch_val('svb.log', case.flag)
                    self.patch_val('svb.util.SVB_LOG', case.env)

                    logging_func('foo \nbar', y=3)  # function under test

                    if case.should_output:
                        print_mock.assert_called_once_with(
                            "message='foo \\nbar' y=3",
                            file=sys.stderr,
                        )
                    else:
                        print_mock.assert_not_called()
                    logger_mock.assert_called_once_with(
                        "message='foo \\nbar' y=3")
                finally:
                    self.doCleanups()

    def test_log_debug(self):
        # (SVB_LOG, svb.log): should_output?
        test_cases = [
            LogTestCase(env=None, flag=None, should_output=False),
            LogTestCase(env=None, flag='debug', should_output=True),
            LogTestCase(env=None, flag='info', should_output=False),
            LogTestCase(env='debug', flag=None, should_output=True),
            LogTestCase(env='debug', flag='debug', should_output=True),
            LogTestCase(env='debug', flag='info', should_output=False),
            LogTestCase(env='info', flag=None, should_output=False),
            LogTestCase(env='info', flag='debug', should_output=True),
            LogTestCase(env='info', flag='info', should_output=False),
        ]
        self.log_test_loop(
            test_cases,
            logging_func=util.log_debug,
            logger_name='svb.util.logger.debug',
        )

    def test_log_info(self):
        # (SVB_LOG, svb.log): should_output?
        test_cases = [
            LogTestCase(env=None, flag=None, should_output=False),
            LogTestCase(env=None, flag='debug', should_output=True),
            LogTestCase(env=None, flag='info', should_output=True),
            LogTestCase(env='debug', flag=None, should_output=True),
            LogTestCase(env='debug', flag='debug', should_output=True),
            LogTestCase(env='debug', flag='info', should_output=True),
            LogTestCase(env='info', flag=None, should_output=True),
            LogTestCase(env='info', flag='debug', should_output=True),
            LogTestCase(env='info', flag='info', should_output=True),
        ]
        self.log_test_loop(
            test_cases,
            logging_func=util.log_info,
            logger_name='svb.util.logger.info',
        )

    def test_logfmt(self):
        cases = [
            FmtTestCase(props={'foo': 'bar', 'message': 'yes'},
                        expected='foo=bar message=yes'),
            FmtTestCase(props={'foo': 'bar baz'},
                        expected="foo='bar baz'"),
            FmtTestCase(props={'b': 2, 'a': 1, 'c': 3},
                        expected='a=1 b=2 c=3'),
            FmtTestCase(props={'key with space': True},
                        expected="'key with space'=True"),
        ]
        for case in cases:
            with self.subTest(props=case.props):
                result = util.logfmt(case.props)
                self.assertEqual(result, case.expected)
