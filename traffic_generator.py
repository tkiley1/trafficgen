#!/usr/bin/env python3
"""
Simple Web Traffic Generator
Generates traffic to random websites on the internet.
"""

import random
import time
import requests
import logging
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
import argparse
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('traffic_generator.log')
    ]
)
logger = logging.getLogger(__name__)

# List of popular websites to visit
WEBSITES = [
    "https://www.google.com",
    "https://www.github.com",
    "https://www.stackoverflow.com",
    "https://www.wikipedia.org",
    "https://www.reddit.com",
    "https://www.youtube.com",
    "https://www.amazon.com",
    "https://www.netflix.com",
    "https://www.twitter.com",
    "https://www.linkedin.com",
    "https://www.medium.com",
    "https://www.dev.to",
    "https://www.hackernews.com",
    "https://www.producthunt.com",
    "https://www.techcrunch.com",
    "https://www.ars-technica.com",
    "https://www.theverge.com",
    "https://www.wired.com",
    "https://www.cnn.com",
    "https://www.bbc.com",
    "https://www.nytimes.com",
    "https://www.washingtonpost.com",
    "https://www.economist.com",
    "https://www.nature.com",
    "https://www.science.org",
    "https://www.arxiv.org",
    "https://www.researchgate.net",
    "https://www.academia.edu",
    "https://www.coursera.org",
    "https://www.edx.org",
    "https://www.udemy.com",
    "https://www.freecodecamp.org",
    "https://www.codecademy.com",
    "https://www.theodinproject.com",
    "https://www.frontendmentor.io",
    "https://www.css-tricks.com",
    "https://www.smashingmagazine.com",
    "https://www.alistapart.com",
    "https://www.web.dev",
    "https://www.mozilla.org",
    "https://www.python.org",
    "https://www.nodejs.org",
    "https://www.reactjs.org",
    "https://www.vuejs.org",
    "https://www.angular.io",
    "https://www.docker.com",
    "https://www.kubernetes.io",
    "https://www.terraform.io",
    "https://www.ansible.com"
]


class TrafficGenerator:
    def __init__(self, max_workers=5, delay_range=(1, 5), timeout=10):
        self.max_workers = max_workers
        self.delay_range = delay_range
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def visit_website(self, url):
        """Visit a single website and log the result."""
        try:
            logger.info(f"Visiting: {url}")
            start_time = time.time()

            response = self.session.get(
                url, timeout=self.timeout, allow_redirects=True)
            end_time = time.time()

            duration = end_time - start_time
            status_code = response.status_code

            if status_code == 200:
                logger.info(
                    f"✅ Success: {url} (Status: {status_code}, Duration: {duration:.2f}s)")
            else:
                logger.warning(
                    f"⚠️  Warning: {url} (Status: {status_code}, Duration: {duration:.2f}s)")

            return {
                'url': url,
                'status_code': status_code,
                'duration': duration,
                'success': status_code == 200
            }

        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout: {url}")
            return {'url': url, 'status_code': None, 'duration': None, 'success': False}
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Connection Error: {url}")
            return {'url': url, 'status_code': None, 'duration': None, 'success': False}
        except Exception as e:
            logger.error(f"❌ Error visiting {url}: {str(e)}")
            return {'url': url, 'status_code': None, 'duration': None, 'success': False}

    def generate_traffic(self, num_requests=None, continuous=False):
        """Generate traffic by visiting random websites."""
        stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_duration': 0
        }

        if continuous:
            logger.info("Starting continuous traffic generation...")
            while True:
                self._process_batch(1, stats)
                delay = random.uniform(*self.delay_range)
                logger.info(
                    f"Waiting {delay:.2f} seconds before next request...")
                time.sleep(delay)
        else:
            if num_requests is None:
                num_requests = len(WEBSITES)

            logger.info(
                f"Starting traffic generation for {num_requests} requests...")
            self._process_batch(num_requests, stats)

        self._print_stats(stats)

    def _process_batch(self, num_requests, stats):
        """Process a batch of requests."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Select random websites
            selected_urls = random.sample(
                WEBSITES, min(num_requests, len(WEBSITES)))

            # Submit requests
            future_to_url = {executor.submit(
                self.visit_website, url): url for url in selected_urls}

            # Collect results
            for future in future_to_url:
                result = future.result()
                stats['total_requests'] += 1

                if result['success']:
                    stats['successful_requests'] += 1
                    if result['duration']:
                        stats['total_duration'] += result['duration']
                else:
                    stats['failed_requests'] += 1

    def _print_stats(self, stats):
        """Print traffic generation statistics."""
        logger.info("=" * 50)
        logger.info("TRAFFIC GENERATION STATISTICS")
        logger.info("=" * 50)
        logger.info(f"Total Requests: {stats['total_requests']}")
        logger.info(f"Successful: {stats['successful_requests']}")
        logger.info(f"Failed: {stats['failed_requests']}")

        if stats['successful_requests'] > 0:
            avg_duration = stats['total_duration'] / \
                stats['successful_requests']
            logger.info(f"Average Response Time: {avg_duration:.2f}s")

        success_rate = (stats['successful_requests'] /
                        stats['total_requests']) * 100
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description='Simple Web Traffic Generator')
    parser.add_argument('--requests', '-r', type=int, default=None,
                        help='Number of requests to make (default: all websites)')
    parser.add_argument('--continuous', '-c', action='store_true',
                        help='Run continuously until stopped')
    parser.add_argument('--workers', '-w', type=int, default=5,
                        help='Number of concurrent workers (default: 5)')
    parser.add_argument('--delay-min', type=float, default=1.0,
                        help='Minimum delay between requests in seconds (default: 1.0)')
    parser.add_argument('--delay-max', type=float, default=5.0,
                        help='Maximum delay between requests in seconds (default: 5.0)')
    parser.add_argument('--timeout', '-t', type=int, default=10,
                        help='Request timeout in seconds (default: 10)')

    args = parser.parse_args()

    # Validate arguments
    if args.requests is not None and args.requests <= 0:
        logger.error("Number of requests must be positive")
        sys.exit(1)

    if args.delay_min < 0 or args.delay_max < 0:
        logger.error("Delay values must be non-negative")
        sys.exit(1)

    if args.delay_min > args.delay_max:
        logger.error("Minimum delay cannot be greater than maximum delay")
        sys.exit(1)

    # Create and run traffic generator
    generator = TrafficGenerator(
        max_workers=args.workers,
        delay_range=(args.delay_min, args.delay_max),
        timeout=args.timeout
    )

    try:
        generator.generate_traffic(
            num_requests=args.requests,
            continuous=args.continuous
        )
    except KeyboardInterrupt:
        logger.info("Traffic generation stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
