import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from traffic_generator import (
    SiteStore,
    TrafficGenerator,
    create_web_server,
    destination_is_public,
    validate_site_url,
)


class SiteStoreTests(unittest.TestCase):
    def test_replace_normalizes_duplicates(self):
        store = SiteStore(["https://example.com"])

        sites = store.replace(
            [" https://github.com ", "https://github.com", "https://python.org/docs"]
        )

        self.assertEqual(sites, ["https://github.com", "https://python.org/docs"])

    def test_replace_rejects_unsafe_url_shapes(self):
        invalid_urls = [
            "http://example.com",
            "https://user:password@example.com",
            "https://example.com:8443",
            "https://example.com/#fragment",
            "https://127.0.0.1",
            "https://service.internal",
        ]

        for url in invalid_urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_site_url(url)

    def test_private_destination_is_blocked(self):
        self.assertFalse(destination_is_public("https://127.0.0.1"))


class WebApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        frontend = Path(self.temp_dir.name) / "index.html"
        frontend.write_text("<h1>TrafficGen</h1>", encoding="utf-8")
        self.store = SiteStore(["https://example.com"])
        self.generator = TrafficGenerator(self.store)
        self.server = create_web_server(
            self.store,
            self.generator,
            host="127.0.0.1",
            port=0,
            frontend_path=frontend,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def request_json(self, path, method="GET", payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read())

    def test_health_and_frontend_are_served(self):
        status, payload = self.request_json("/healthz")
        with urllib.request.urlopen(self.base_url + "/", timeout=2) as response:
            frontend = response.read().decode()

        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})
        self.assertIn("TrafficGen", frontend)

    def test_site_update_applies_to_generator_store(self):
        status, payload = self.request_json(
            "/api/sites",
            method="PUT",
            payload={"sites": ["https://github.com", "https://python.org"]},
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["sites"], self.store.snapshot())

    def test_invalid_site_update_returns_bad_request(self):
        request = urllib.request.Request(
            self.base_url + "/api/sites",
            data=json.dumps({"sites": ["https://127.0.0.1"]}).encode(),
            method="PUT",
            headers={"Content-Type": "application/json"},
        )

        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(request, timeout=2)

        self.assertEqual(raised.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
