# Web Traffic Generator

A simple Python-based web traffic generator that visits random websites on the internet. This tool is designed to run in Docker and can generate realistic web traffic patterns.

## Features

- 🚀 **Multi-threaded**: Concurrent requests with configurable worker count
- 🌐 **Realistic Traffic**: Visits popular websites with realistic delays
- 📊 **Statistics**: Detailed logging and performance metrics
- 🐳 **Docker Ready**: Easy deployment with Docker and Docker Compose
- ⚙️ **Configurable**: Customizable request patterns and timing
- 🔒 **Secure**: Runs as non-root user in container

## Quick Start

### Using Docker Compose (Recommended)

1. **Build and run the container:**
   ```bash
   docker-compose up --build
   ```

2. **Run in background:**
   ```bash
   docker-compose up -d --build
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Stop the container:**
   ```bash
   docker-compose down
   ```

### Using Docker directly

1. **Build the image:**
   ```bash
   docker build -t traffic-generator .
   ```

2. **Run the container:**
   ```bash
   # Continuous mode (default)
   docker run --name traffic-generator traffic-generator
   
   # Specific number of requests
   docker run --name traffic-generator traffic-generator python traffic_generator.py --requests 10
   
   # Custom configuration
   docker run --name traffic-generator traffic-generator python traffic_generator.py --continuous --workers 5 --delay-min 1 --delay-max 5
   ```

## Configuration Options

### Command Line Arguments

| Argument | Short | Default | Description |
|----------|-------|---------|-------------|
| `--requests` | `-r` | All websites | Number of requests to make |
| `--continuous` | `-c` | False | Run continuously until stopped |
| `--workers` | `-w` | 5 | Number of concurrent workers |
| `--delay-min` | | 1.0 | Minimum delay between requests (seconds) |
| `--delay-max` | | 5.0 | Maximum delay between requests (seconds) |
| `--timeout` | `-t` | 10 | Request timeout in seconds |

### Usage Examples

```bash
# Visit all websites once
python traffic_generator.py

# Visit 10 random websites
python traffic_generator.py --requests 10

# Run continuously with 3 workers
python traffic_generator.py --continuous --workers 3

# Fast traffic generation (1-3 second delays)
python traffic_generator.py --continuous --workers 10 --delay-min 1 --delay-max 3

# Slow, realistic traffic (5-15 second delays)
python traffic_generator.py --continuous --workers 2 --delay-min 5 --delay-max 15

# Custom timeout for slow connections
python traffic_generator.py --timeout 30 --continuous
```

## Docker Compose Configuration

The `docker-compose.yml` file includes several pre-configured scenarios. You can modify the `command` line to use different configurations:

```yaml
# For a specific number of requests:
command: ["python", "traffic_generator.py", "--requests", "10", "--workers", "5"]

# For faster traffic:
command: ["python", "traffic_generator.py", "--continuous", "--workers", "10", "--delay-min", "1", "--delay-max", "3"]

# For slower, more realistic traffic:
command: ["python", "traffic_generator.py", "--continuous", "--workers", "2", "--delay-min", "5", "--delay-max", "15"]
```

## Websites Visited

The traffic generator visits a curated list of popular websites including:

- **Search & Social**: Google, Reddit, Twitter, LinkedIn
- **Tech & Development**: GitHub, Stack Overflow, Dev.to, Hacker News
- **News & Media**: CNN, BBC, TechCrunch, The Verge
- **Education**: Coursera, edX, freeCodeCamp, Codecademy
- **Research**: arXiv, ResearchGate, Nature, Science
- **And many more...**

## Logging

The application provides detailed logging with:
- Request status and timing
- Success/failure rates
- Performance statistics
- Error handling

Logs are written to both console and `traffic_generator.log` file.

## Security Considerations

- Runs as non-root user in Docker container
- Uses realistic User-Agent headers
- Configurable timeouts to prevent hanging requests
- Graceful error handling for network issues

## Monitoring

You can monitor the traffic generator using:

```bash
# View real-time logs
docker-compose logs -f

# Check container status
docker ps

# View resource usage
docker stats traffic-generator
```

## Troubleshooting

### Common Issues

1. **Container exits immediately:**
   - Check logs: `docker-compose logs`
   - Verify network connectivity
   - Check if websites are accessible

2. **High failure rate:**
   - Increase timeout: `--timeout 30`
   - Reduce worker count: `--workers 2`
   - Check network stability

3. **Too much traffic:**
   - Increase delays: `--delay-min 5 --delay-max 15`
   - Reduce workers: `--workers 1`

### Performance Tuning

- **For high-traffic scenarios**: Increase workers, reduce delays
- **For realistic traffic**: Use 2-3 workers with 5-15 second delays
- **For testing**: Use 1-2 workers with longer delays

## License

This project is open source and available under the MIT License.

## Disclaimer

This tool is intended for legitimate testing and educational purposes only. Please ensure you comply with the terms of service of any websites you visit and respect rate limits and robots.txt files.
