
#!/bin/bash
echo "🚀 Starting Yidun Solver on Railway"
echo "==================================="
echo "PORT: $PORT"
echo "Python: $(python --version)"
echo "Memory: $(free -h | grep Mem | awk '{print $2}')"
echo "==================================="

# Start the server
hypercorn app:app --bind 0.0.0.0:$PORT --workers 1