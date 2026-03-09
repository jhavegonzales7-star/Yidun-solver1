#!/usr/bin/env python3
"""
Yidun (NetEase) Captcha Solver API Server
Complete fixed version for Railway.app
"""

import os
import sys
import time
import json
import random
import logging
import argparse
import threading
import gc
import traceback
from datetime import datetime
from functools import lru_cache

# Web framework - using Flask instead of Quart for better Railway compatibility
from flask import Flask, request, jsonify
from flask_cors import CORS

# Utilities
from fake_useragent import UserAgent

# ============================================
# COLORED LOGGING
# ============================================

COLORS = {
    'MAGENTA': '\033[35m',
    'BLUE': '\033[34m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'RED': '\033[31m',
    'RESET': '\033[0m',
}

class CustomLogger:
    """Custom logger with colored output"""
    
    def __init__(self, name):
        self.name = name
        self.debug_mode = False
    
    def _format_message(self, level: str, color: str, message: str) -> str:
        timestamp = datetime.now().strftime('%H:%M:%S')
        return f"[{timestamp}] [{COLORS.get(color)}{level}{COLORS.get('RESET')}] {message}"
    
    def debug(self, message: str):
        if self.debug_mode:
            print(self._format_message('DEBUG', 'MAGENTA', message))
    
    def info(self, message: str):
        print(self._format_message('INFO', 'BLUE', message))
    
    def success(self, message: str):
        print(self._format_message('SUCCESS', 'GREEN', message))
    
    def warning(self, message: str):
        print(self._format_message('WARNING', 'YELLOW', message))
    
    def error(self, message: str):
        print(self._format_message('ERROR', 'RED', message))

# Setup logger
logger = CustomLogger("YidunAPI")

# ============================================
# TRY TO IMPORT SOLVER
# ============================================

SOLVER_AVAILABLE = False
try:
    # Try to import the solver modules
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # These will be imported from your files
    # from yidun_proxyless import Dun163, initialize_global_model, get_compiled_js
    
    # For now, we'll use mock classes
    SOLVER_AVAILABLE = False
    logger.warning("Solver modules not found - running in mock mode")
except ImportError as e:
    logger.warning(f"Solver import error: {e}")
    SOLVER_AVAILABLE = False

# ============================================
# MOCK SOLVER (For testing)
# ============================================

class MockDun163:
    """Mock solver for testing"""
    def __init__(self, id_, referer, fp_h, ua, thread_id, domain):
        self.id_ = id_
        self.referer = referer
        self.fp_h = fp_h
        self.ua = ua
        self.thread_id = thread_id
        self.domain = domain
        self.resp_json2 = None
        self.ctx = None
        self.fp = f"mock_fp_{random.randint(100000, 999999)}"
        logger.debug(f"Mock solver created for {id_}")
    
    def run(self):
        """Mock run method"""
        import time
        time.sleep(1.5)  # Simulate processing
        self.resp_json2 = {
            'result': True,
            'validate': f'mock_validate_{random.randint(100000000, 999999999)}'
        }
        return True

# ============================================
# MEMORY MANAGEMENT
# ============================================

def get_memory_usage() -> float:
    """Get current memory usage in MB"""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        return 0.0

def force_garbage_collect() -> float:
    """Force garbage collection to free memory"""
    collected = gc.collect()
    logger.debug(f"Garbage collected: {collected} objects")
    return get_memory_usage()

# ============================================
# FLASK APP
# ============================================

app = Flask(__name__)
CORS(app)

# Server stats
start_time = time.time()
request_count = 0
success_count = 0
fail_count = 0

@app.before_request
def before_request():
    """Log each request"""
    global request_count
    request_count += 1
    logger.debug(f"Request #{request_count} from {request.remote_addr}")

@app.route('/', methods=['GET'])
def index():
    """Home page with API documentation"""
    memory = get_memory_usage()
    uptime = time.time() - start_time
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Yidun Captcha Solver API</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-900 text-gray-200 min-h-screen">
        <div class="container mx-auto px-4 py-8">
            <div class="max-w-4xl mx-auto">
                <div class="bg-gray-800 rounded-lg shadow-xl p-6 mb-8">
                    <h1 class="text-3xl font-bold text-center mb-2 text-blue-400">🛡️ Yidun Captcha Solver API</h1>
                    <p class="text-gray-400 text-center mb-6">NetEase Yidun (dun.163.com) solving service</p>
                    
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                        <div class="bg-gray-700 p-3 rounded-lg text-center">
                            <div class="text-green-400 text-xl mb-1">{'✅' if SOLVER_AVAILABLE else '⚠️'}</div>
                            <div class="text-xs text-gray-400">Solver</div>
                        </div>
                        <div class="bg-gray-700 p-3 rounded-lg text-center">
                            <div class="text-blue-400 text-xl mb-1">{memory:.0f} MB</div>
                            <div class="text-xs text-gray-400">Memory</div>
                        </div>
                        <div class="bg-gray-700 p-3 rounded-lg text-center">
                            <div class="text-yellow-400 text-xl mb-1">{hours}h {minutes}m</div>
                            <div class="text-xs text-gray-400">Uptime</div>
                        </div>
                        <div class="bg-gray-700 p-3 rounded-lg text-center">
                            <div class="text-purple-400 text-xl mb-1">{request_count}</div>
                            <div class="text-xs text-gray-400">Requests</div>
                        </div>
                    </div>
                    
                    <div class="grid md:grid-cols-2 gap-6">
                        <div class="bg-gray-700 p-4 rounded-lg">
                            <h2 class="text-xl font-semibold mb-3 text-blue-400">GET /solve</h2>
                            <p class="text-sm text-gray-300 mb-2">Query parameters:</p>
                            <ul class="space-y-1 text-sm">
                                <li><span class="text-yellow-400">id</span> - Captcha ID (optional)</li>
                                <li><span class="text-yellow-400">referer</span> - Referer URL (optional)</li>
                                <li><span class="text-yellow-400">ua</span> - User-Agent (optional)</li>
                            </ul>
                        </div>
                        
                        <div class="bg-gray-700 p-4 rounded-lg">
                            <h2 class="text-xl font-semibold mb-3 text-green-400">POST /solve</h2>
                            <p class="text-sm text-gray-300 mb-2">JSON body:</p>
                            <pre class="bg-gray-900 p-2 rounded text-xs overflow-x-auto">
{{
    "id": "fef5c67c39074e9d845f4bf579cc07af",
    "referer": "https://mtacc.mobilelegends.com/",
    "ua": "Mozilla/5.0 ..."
}}
                            </pre>
                        </div>
                    </div>
                    
                    <div class="mt-6 bg-gray-700 p-4 rounded-lg">
                        <h2 class="text-xl font-semibold mb-3 text-purple-400">Example Usage</h2>
                        <pre class="bg-gray-900 p-3 rounded text-sm overflow-x-auto">
# POST request
curl -X POST https://yidun-solver.up.railway.app/solve \\
     -H "Content-Type: application/json" \\
     -d '{{"id": "fef5c67c39074e9d845f4bf579cc07af"}}'
                        </pre>
                    </div>
                    
                    <div class="mt-6 text-center text-sm text-gray-500">
                        <p>Other endpoints: 
                            <a href="/health" class="text-blue-400 hover:underline">/health</a> | 
                            <a href="/stats" class="text-blue-400 hover:underline">/stats</a>
                        </p>
                    </div>
                    
                    <div class="mt-4 text-center text-xs text-gray-600">
                        <p>Running on Railway.app • 1GB RAM • Python 3.10</p>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    memory = get_memory_usage()
    status = 'healthy' if memory < 900 else 'degraded'
    
    return jsonify({
        'status': status,
        'timestamp': datetime.now().isoformat(),
        'memory_mb': round(memory, 1),
        'requests_served': request_count,
        'solver_available': SOLVER_AVAILABLE
    })

@app.route('/stats', methods=['GET'])
def stats():
    """Statistics endpoint"""
    memory = get_memory_usage()
    uptime = time.time() - start_time
    
    return jsonify({
        'server': {
            'start_time': datetime.fromtimestamp(start_time).isoformat(),
            'uptime_seconds': round(uptime, 2),
            'uptime_human': f"{int(uptime//3600)}h {int((uptime%3600)//60)}m",
            'requests_served': request_count,
            'success_count': success_count,
            'fail_count': fail_count,
            'success_rate': round((success_count / max(request_count, 1)) * 100, 1)
        },
        'memory': {
            'current_mb': round(memory, 1),
            'limit_mb': 1024,
            'usage_percent': round((memory/1024)*100, 1)
        },
        'solver': {
            'available': SOLVER_AVAILABLE,
            'mock_mode': not SOLVER_AVAILABLE
        }
    })

@app.route('/solve', methods=['GET', 'POST'])
def solve():
    """Main solving endpoint"""
    global success_count, fail_count
    
    req_id = request_count
    
    # Parse request
    if request.method == 'GET':
        id_ = request.args.get('id', "fef5c67c39074e9d845f4bf579cc07af")
        referer = request.args.get('referer', "https://mtacc.mobilelegends.com/")
        fp_h = request.args.get('fp_h', "mtacc.mobilelegends.com")
        ua = request.args.get('ua')
        domain = request.args.get('domain', "https://c.dun.163.com")
    else:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data'}), 400
        
        id_ = data.get('id', "fef5c67c39074e9d845f4bf579cc07af")
        referer = data.get('referer', "https://mtacc.mobilelegends.com/")
        fp_h = data.get('fp_h', "mtacc.mobilelegends.com")
        ua = data.get('ua')
        domain = data.get('domain', "https://c.dun.163.com")
    
    # Generate UA if not provided
    if not ua:
        try:
            ua = UserAgent().random
        except:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    logger.info(f"[{req_id}] 📝 Request | ID: {id_[:16]}...")
    
    start_time_req = time.time()
    
    try:
        # Use mock solver for now
        solver = MockDun163(
            id_=id_,
            referer=referer,
            fp_h=fp_h,
            ua=ua,
            thread_id=req_id,
            domain=domain
        )
        
        # Run solver
        success = solver.run()
        elapsed = time.time() - start_time_req
        
        if success and hasattr(solver, 'resp_json2'):
            validate = solver.resp_json2.get('validate', '')
            success_count += 1
            
            logger.success(f"[{req_id}] ✅ Solved in {elapsed:.2f}s")
            
            return jsonify({
                'success': True,
                'validate': validate,
                'token': f"token_{validate}",  # Simplified
                'elapsed_time': round(elapsed, 3),
                'request_id': req_id
            })
        else:
            fail_count += 1
            logger.error(f"[{req_id}] ❌ Failed in {elapsed:.2f}s")
            
            return jsonify({
                'success': False,
                'error': 'Failed to solve captcha',
                'elapsed_time': round(elapsed, 3)
            }), 422
            
    except Exception as e:
        elapsed = time.time() - start_time_req
        fail_count += 1
        logger.error(f"[{req_id}] 💥 Error: {str(e)}")
        
        return jsonify({
            'success': False,
            'error': str(e),
            'elapsed_time': round(elapsed, 3)
        }), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    # Get port from environment
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info("=" * 60)
    logger.info("🚀 YIDUN CAPTCHA SOLVER API SERVER")
    logger.info("=" * 60)
    logger.info(f"📡 Port: {port}")
    logger.info(f"🐛 Debug: {debug}")
    logger.info(f"💾 Memory: {get_memory_usage():.1f} MB")
    logger.info(f"🎭 Mode: {'MOCK' if not SOLVER_AVAILABLE else 'REAL'}")
    logger.info("=" * 60)
    
    # Run Flask
    app.run(host='0.0.0.0', port=port, debug=debug)