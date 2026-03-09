#!/usr/bin/env python3
"""
Yidun Captcha Solver API - Flask Version for Railway
"""

import os
import sys
import time
import json
import random
import logging
import threading
import gc
import traceback
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# Import solver
try:
    from yidun_proxyless import Dun163, initialize_global_model, get_compiled_js
    SOLVER_AVAILABLE = True
except:
    SOLVER_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("YidunAPI")

# Create Flask app
app = Flask(__name__)
CORS(app)

# Stats
start_time = time.time()
request_count = 0
success_count = 0
fail_count = 0

@app.route('/')
def index():
    return jsonify({
        "name": "Yidun Captcha Solver API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": ["/health", "/stats", "/solve"]
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "requests": request_count
    })

@app.route('/stats')
def stats():
    return jsonify({
        "requests": request_count,
        "success": success_count,
        "fail": fail_count,
        "uptime": time.time() - start_time
    })

@app.route('/solve', methods=['POST'])
def solve():
    global request_count, success_count, fail_count
    request_count += 1
    
    data = request.get_json() or {}
    id_ = data.get('id', "fef5c67c39074e9d845f4bf579cc07af")
    
    logger.info(f"Request #{request_count} for ID: {id_[:16]}...")
    
    # Mock response
    time.sleep(1)
    success_count += 1
    
    return jsonify({
        "success": True,
        "token": f"mock_token_{random.randint(10000, 99999)}",
        "validate": f"mock_validate_{random.randint(10000, 99999)}"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)