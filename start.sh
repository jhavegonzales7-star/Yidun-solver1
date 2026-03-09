
#!/bin/bash
echo "🚀 Starting Yidun Solver API on Railway..."
echo "PORT: $PORT"
echo "RAILWAY_ENVIRONMENT: $RAILWAY_ENVIRONMENT"

# Print system info
echo "System Info:"
echo "- CPU: $(nproc) cores"
echo "- Memory: $(free -h | grep Mem | awk '{print $2}')"
echo "- Python: $(python --version)"

# Start the server
python yidun_api.py --host 0.0.0.0 --port $PORT --threads 2