"""Exported registration forms must match the Developer Center contract."""

import unittest

from tests import test_protocol as protocol


class OnboardingContractTests(unittest.TestCase):
    def test_anonymous_b_export_disables_a_without_omitting_required_object(self):
        case = protocol.ProtocolTests()
        case.setUp()
        self.addCleanup(case.tearDown)
        response = case.app.test_client().get(
            "/onboarding.json?flow=b", base_url=protocol.ORIGIN
        )
        self.assertEqual(response.status_code, 200)
        form = response.json
        self.assertEqual(
            form["direction_a"], {"redirect_uris": [], "login_enabled": False}
        )
        self.assertEqual(len(form["direction_b"]["services"]), 5)
        self.assertNotIn("joint", form)
