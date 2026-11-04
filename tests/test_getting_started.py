import unittest
from html import unescape
from html.parser import HTMLParser

from partner.i18n import MESSAGES
from tests import test_protocol as protocol


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.targets.append(dict(attrs).get("href"))


class GettingStartedTests(unittest.TestCase):
    def test_anonymous_developer_can_choose_and_prepare_every_flow_without_demo_access(self):
        case = protocol.ProtocolTests()
        case.setUp()
        try:
            for locale in ("en", "ko", "ja"):
                with self.subTest(locale=locale):
                    client = case.app.test_client()
                    response = client.get(
                        "/", base_url=protocol.ORIGIN, headers={"Accept-Language": locale}
                    )
                    self.assertEqual(response.status_code, 200)
                    page = unescape(response.text)
                    links = Links()
                    links.feed(page)
                    for flow in ("login", "a", "b", "joint"):
                        self.assertIn("/onboarding.json?flow=" + flow, links.targets)
                        self.assertIn(MESSAGES["goal_" + flow][locale], page)
                        self.assertIn(MESSAGES["success_" + flow][locale], page)
                    self.assertIn(
                        "https://github.com/TheTechclip/musecat-partner-example/tree/code/pr99-example-integration",
                        links.targets,
                    )
                    self.assertTrue(any("docs/local-development.md" in (url or "") for url in links.targets))
                    route_locale = {"ko": "kr", "ja": "jp"}.get(locale, locale)
                    self.assertIn(
                        case.app.config["MUSECAT_WEB_ORIGIN"] + "/" + route_locale + "/developer/apps",
                        links.targets,
                    )
                    self.assertIn(MESSAGES["json_boundary"][locale], page)
                    self.assertIn(MESSAGES["demo_access"][locale], page)
                    self.assertLess(page.index('id="prepare"'), page.index('href="/login"'))
                    self.assertNotIn(case.config["DEMO_PASSWORD"], page)
                    self.assertNotIn(case.config["MUSECAT_CLIENT_SECRET"], page)
        finally:
            case.tearDown()
