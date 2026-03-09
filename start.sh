
echo " Starting Yidun Solver"
echo "==================================="
echo "PORT: $PORT"
echo "Python: $(python --version)"
echo "Memory: $(free -h | grep Mem | awk '{print $2}')"
echo "==================================="

python app.py --host 0.0.0.0 --port $PORT --threads 1