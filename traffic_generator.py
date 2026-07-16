#!/usr/bin/env python3
"""Generate web traffic and expose a small control surface for target sites."""

import argparse
import ipaddress
import json
import logging
import os
import random
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import requests


def configure_logging():
    handlers = [logging.StreamHandler(sys.stdout)]
    log_dir = Path.cwd() / "logs"
    try:
        log_dir.mkdir(exist_ok=True)
        handlers.append(logging.FileHandler(log_dir / "traffic_generator.log"))
    except OSError:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


configure_logging()
logger = logging.getLogger(__name__)

DEFAULT_WEBSITES = (
    "https://www.google.com",
    "https://www.github.com",
    "https://www.stackoverflow.com",
    "https://www.wikipedia.org",
    "https://www.reddit.com",
    "https://www.youtube.com",
    "https://www.amazon.com",
    "https://www.netflix.com",
    "https://www.linkedin.com",
    "https://www.dev.to",
    "https://news.ycombinator.com",
    "https://www.techcrunch.com",
    "https://www.theverge.com",
    "https://www.wired.com",
    "https://www.bbc.com",
    "https://www.nature.com",
    "https://www.python.org",
    "https://www.docker.com",
    "https://www.kubernetes.io",
    "https://www.terraform.io",
)
MAX_SITES = 100
MAX_URL_LENGTH = 2048
MAX_REQUEST_BODY = 64 * 1024


def validate_site_url(value):
    if not isinstance(value, str):
        raise ValueError("Each site must be a URL string")
    value = value.strip()
    if not value or len(value) > MAX_URL_LENGTH:
        raise ValueError("Site URLs must be between 1 and 2048 characters")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Only HTTPS URLs with a hostname are allowed")
    if parsed.username or parsed.password:
        raise ValueError("Credentials are not allowed in site URLs")
    if parsed.port not in (None, 443):
        raise ValueError("Only the standard HTTPS port is allowed")
    if parsed.fragment:
        raise ValueError("URL fragments are not allowed")
    hostname = parsed.hostname.lower()
    if hostname == "localhost" or hostname.endswith(
        (".localhost", ".local", ".internal")
    ):
        raise ValueError("Private hostnames are not allowed")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("Private IP addresses are not allowed")
    return value


def destination_is_public(url):
    """Resolve a target immediately before use and reject non-public addresses."""
    hostname = urlparse(url).hostname
    if not hostname:
        return False
    try:
        addresses = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False
    if not addresses:
        return False
    try:
        return all(ipaddress.ip_address(item[4][0]).is_global for item in addresses)
    except ValueError:
        return False


class SiteStore:
    def __init__(self, sites=DEFAULT_WEBSITES):
        self._lock = threading.RLock()
        self._sites = list(sites)

    def snapshot(self):
        with self._lock:
            return list(self._sites)

    def replace(self, sites):
        if not isinstance(sites, list):
            raise ValueError("sites must be an array")
        if not sites or len(sites) > MAX_SITES:
            raise ValueError(f"Provide between 1 and {MAX_SITES} sites")
        validated = []
        seen = set()
        for site in sites:
            normalized = validate_site_url(site)
            if normalized not in seen:
                validated.append(normalized)
                seen.add(normalized)
        if not validated:
            raise ValueError("Provide at least one unique site")
        with self._lock:
            self._sites = validated
        return self.snapshot()


class TrafficGenerator:
    def __init__(self, site_store, max_workers=5, delay_range=(1, 5), timeout=10):
        self.site_store = site_store
        self.max_workers = max_workers
        self.delay_range = delay_range
        self.timeout = timeout
        self.started_at = time.time()
        self._stats_lock = threading.Lock()
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_duration": 0.0,
        }
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "Chrome/126.0 Safari/537.36 TrafficGen/2.0"
                )
            }
        )

    def status(self):
        with self._stats_lock:
            stats = dict(self._stats)
        successful = stats["successful_requests"]
        stats["average_duration"] = (
            round(stats["total_duration"] / successful, 3) if successful else 0
        )
        stats["uptime_seconds"] = int(time.time() - self.started_at)
        stats["site_count"] = len(self.site_store.snapshot())
        stats.pop("total_duration")
        return stats

    def visit_website(self, url):
        if not destination_is_public(url):
            logger.error("Blocked non-public or unresolved destination: %s", url)
            return {"url": url, "status_code": None, "duration": None, "success": False}
        try:
            logger.info("Visiting: %s", url)
            started_at = time.time()
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=False,
            )
            duration = time.time() - started_at
            successful = 200 <= response.status_code < 400
            log = logger.info if successful else logger.warning
            log(
                "Result: %s (status=%s, duration=%.2fs)",
                url,
                response.status_code,
                duration,
            )
            return {
                "url": url,
                "status_code": response.status_code,
                "duration": duration,
                "success": successful,
            }
        except requests.exceptions.Timeout:
            logger.error("Timeout: %s", url)
        except requests.exceptions.ConnectionError:
            logger.error("Connection error: %s", url)
        except requests.RequestException as error:
            logger.error("Request error for %s: %s", url, error)
        return {"url": url, "status_code": None, "duration": None, "success": False}

    def generate_traffic(self, num_requests=None, continuous=False):
        if continuous:
            logger.info("Starting continuous traffic generation")
            while True:
                self._process_batch(1)
                delay = random.uniform(*self.delay_range)
                logger.info("Waiting %.2f seconds before next request", delay)
                time.sleep(delay)
        else:
            sites = self.site_store.snapshot()
            request_count = num_requests if num_requests is not None else len(sites)
            logger.info("Starting traffic generation for %s requests", request_count)
            self._process_batch(request_count)
            self._print_stats()

    def _process_batch(self, num_requests):
        sites = self.site_store.snapshot()
        selected_urls = random.sample(sites, min(num_requests, len(sites)))
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self.visit_website, url) for url in selected_urls
            ]
            for future in futures:
                result = future.result()
                with self._stats_lock:
                    self._stats["total_requests"] += 1
                    if result["success"]:
                        self._stats["successful_requests"] += 1
                        if result["duration"]:
                            self._stats["total_duration"] += result["duration"]
                    else:
                        self._stats["failed_requests"] += 1

    def _print_stats(self):
        stats = self.status()
        logger.info(
            "Traffic stats: total=%s successful=%s failed=%s average=%.2fs",
            stats["total_requests"],
            stats["successful_requests"],
            stats["failed_requests"],
            stats["average_duration"],
        )


def make_request_handler(site_store, generator, frontend_path=None):
    frontend_path = frontend_path or Path(__file__).with_name("index.html")

    class TrafficRequestHandler(BaseHTTPRequestHandler):
        server_version = "TrafficGen/2.0"

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                self._send_frontend()
            elif path == "/healthz":
                self._send_json({"status": "ok"})
            elif path == "/api/sites":
                self._send_json({"sites": site_store.snapshot()})
            elif path == "/api/status":
                self._send_json(generator.status())
            else:
                self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

        def do_PUT(self):
            if self.path.split("?", 1)[0] != "/api/sites":
                self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
                return
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                if content_length <= 0 or content_length > MAX_REQUEST_BODY:
                    raise ValueError("Request body is empty or too large")
                payload = json.loads(self.rfile.read(content_length))
                if not isinstance(payload, dict):
                    raise ValueError("Request body must be an object")
                sites = site_store.replace(payload.get("sites"))
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            logger.info("Activated %s traffic targets", len(sites))
            self._send_json({"sites": sites})

        def _send_frontend(self):
            try:
                content = frontend_path.read_bytes()
            except OSError:
                self._send_json(
                    {"error": "Frontend asset is unavailable"},
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return
            self.send_response(HTTPStatus.OK)
            self._security_headers("text/html; charset=utf-8", len(content))
            self.end_headers()
            self.wfile.write(content)

        def _send_json(self, payload, status=HTTPStatus.OK):
            content = json.dumps(payload, separators=(",", ":")).encode()
            self.send_response(status)
            self._security_headers("application/json", len(content))
            self.end_headers()
            self.wfile.write(content)

        def _security_headers(self, content_type, content_length):
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(content_length))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; connect-src 'self'",
            )

        def log_message(self, message, *args):
            logger.info("HTTP %s - %s", self.address_string(), message % args)

    return TrafficRequestHandler


def create_web_server(
    site_store, generator, host="0.0.0.0", port=8080, frontend_path=None
):
    return ThreadingHTTPServer(
        (host, port),
        make_request_handler(site_store, generator, frontend_path),
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Simple Web Traffic Generator")
    parser.add_argument("--requests", "-r", type=int, default=None)
    parser.add_argument("--continuous", "-c", action="store_true")
    parser.add_argument("--workers", "-w", type=int, default=5)
    parser.add_argument("--delay-min", type=float, default=1.0)
    parser.add_argument("--delay-max", type=float, default=5.0)
    parser.add_argument("--timeout", "-t", type=int, default=10)
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    return parser.parse_args()


def main():
    args = parse_args()
    if args.requests is not None and args.requests <= 0:
        raise SystemExit("Number of requests must be positive")
    if args.delay_min < 0 or args.delay_max < 0:
        raise SystemExit("Delay values must be non-negative")
    if args.delay_min > args.delay_max:
        raise SystemExit("Minimum delay cannot be greater than maximum delay")
    if not 1 <= args.port <= 65535:
        raise SystemExit("Port must be between 1 and 65535")

    site_store = SiteStore()
    generator = TrafficGenerator(
        site_store,
        max_workers=args.workers,
        delay_range=(args.delay_min, args.delay_max),
        timeout=args.timeout,
    )
    server = create_web_server(site_store, generator, port=args.port)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    logger.info("Traffic control UI listening on port %s", args.port)

    try:
        generator.generate_traffic(
            num_requests=args.requests,
            continuous=args.continuous,
        )
    except KeyboardInterrupt:
        logger.info("Traffic generation stopped by user")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
