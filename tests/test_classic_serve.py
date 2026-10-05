import functools
import gzip
import http.client
import http.server
import importlib.util
import tempfile
import threading
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("classic_serve", Path(__file__).resolve().parents[1] / "web" / "classic" / "serve.py")
serve = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(serve)


class ServeCompressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        (root / "dist").mkdir()
        (root / "index.html").write_text("<!doctype html><title>Keygen Bench</title><!--OG-->")
        cls.data = ('{"runs": [' + ",".join('{"trace": [[0, 0, 0]]}' for _ in range(500)) + "]}").encode()
        (root / "dist" / "data.json").write_bytes(cls.data)
        (root / "dist" / "tune.mp3").write_bytes(bytes(range(256)) * 8)
        handler = functools.partial(serve.Handler, directory=str(root))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def get(self, path, **headers):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1])
        conn.request("GET", path, headers=headers)
        res = conn.getresponse()
        body = res.read()
        conn.close()
        return res, body

    def test_gzip_when_accepted(self):
        res, body = self.get("/dist/data.json", **{"Accept-Encoding": "gzip, br"})
        self.assertEqual(res.status, 200)
        self.assertEqual(res.getheader("Content-Encoding"), "gzip")
        self.assertEqual(res.getheader("Vary"), "Accept-Encoding")
        self.assertEqual(int(res.getheader("Content-Length")), len(body))
        self.assertLess(len(body), len(self.data))
        self.assertEqual(gzip.decompress(body), self.data)

    def test_identity_without_accept_encoding(self):
        res, body = self.get("/dist/data.json")
        self.assertIsNone(res.getheader("Content-Encoding"))
        self.assertEqual(res.getheader("Vary"), "Accept-Encoding")
        self.assertEqual(body, self.data)

    def test_quality_values_decide_gzip(self):
        cases = {
            "gzip;q=0": None,
            "br, gzip;q=0.5": "gzip",
            "*;q=0.1": "gzip",
            "*, gzip;q=0": None,
            "GZIP; Q=0.000": None,
            "br": None,
        }
        for header, encoding in cases.items():
            with self.subTest(header=header):
                res, body = self.get("/dist/data.json", **{"Accept-Encoding": header})
                self.assertEqual(res.getheader("Content-Encoding"), encoding)
                self.assertEqual(gzip.decompress(body) if encoding else body, self.data)

    def test_range_requests_stay_identity(self):
        res, body = self.get("/dist/data.json", **{"Accept-Encoding": "gzip", "Range": "bytes=2-9"})
        self.assertEqual(res.status, 206)
        self.assertIsNone(res.getheader("Content-Encoding"))
        self.assertEqual(body, self.data[2:10])

    def test_audio_is_never_compressed(self):
        res, _ = self.get("/dist/tune.mp3", **{"Accept-Encoding": "gzip"})
        self.assertIsNone(res.getheader("Content-Encoding"))
        self.assertIsNone(res.getheader("Vary"))

    def test_gzip_revalidation_returns_not_modified(self):
        first, _ = self.get("/dist/data.json", **{"Accept-Encoding": "gzip"})
        res, body = self.get("/dist/data.json", **{"Accept-Encoding": "gzip", "If-Modified-Since": first.getheader("Last-Modified")})
        self.assertEqual(res.status, 304)
        self.assertEqual(body, b"")


if __name__ == "__main__":
    unittest.main()
