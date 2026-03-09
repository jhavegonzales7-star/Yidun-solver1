#!/usr/bin/env python3
"""
Yidun Captcha Solver API - Simplified Flask Version for Railway
"""

import os
import sys
import time
import json
import random
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("yidun-api")

# Create Flask app
app = Flask(__name__)
CORS(app)

# Statistics
start_time = time.time()
request_count = 0
success_count = 0
fail_count = 0

@app.route('/', methods=['GET'])
def home():
    """Home endpoint"""
    return jsonify({
        "name": "Yidun Captcha Solver API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "GET /": "This page",
            "GET /health": "Health check",
            "GET /stats": "Statistics",
            "POST /solve": "Solve captcha"
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": round(time.time() - start_time, 2)
    })

@app.route('/stats', methods=['GET'])
def stats():
    """Statistics endpoint"""
    global request_count, success_count, fail_count
    return jsonify({
        "requests": {
            "total": request_count,
            "success": success_count,
            "fail": fail_count,
            "success_rate": round((success_count / max(request_count, 1)) * 100, 2)
        },
        "uptime": round(time.time() - start_time, 2),
        "memory": {
            "usage": "N/A",
            "limit": "1024 MB"
        }
    })

@app.route('/solve', methods=['POST'])
def solve():
    """Solve captcha endpoint"""
    global request_count, success_count, fail_count
    
    request_count += 1
    
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data"}), 400
        
        # Get parameters
        id_ = data.get('id', "fef5c67c39074e9d845f4bf579cc07af")
        ua = data.get('ua', "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0")
        
        logger.info(f"[{request_count}] Solving captcha for ID: {id_[:16]}...")
        
        # Simulate processing
        time.sleep(1.5)
        
        # Generate mock token
        mock_token = f"mock_token_{random.randint(100000, 999999)}"
        mock_validate = f"mock_validate_{random.randint(100000, 999999)}"
        
        success_count += 1
        logger.info(f"[{request_count}] ✅ Solved successfully")
        
        return jsonify({
            "success": True,
            "token": mock_token,
            "validate": mock_validate,
            "elapsed_time": 1.5,
            "request_id": request_count
        })
        
    except Exception as e:
        fail_count += 1
        logger.error(f"[{request_count}] ❌ Error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "request_id": request_count
        }), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    print("=" * 50)
    print("🚀 YIDUN CAPTCHA SOLVER API")
    print("=" * 50)
    print(f"📡 Port: {port}")
    print(f"🐛 Debug: {debug}")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port, debug=debug)