#!/usr/bin/env python3
"""
Yidun (NetEase) Captcha Solver API Server
Same style as Turnstile Solver - Complete Fixed Version
"""

import os
import sys
import time
import json
import random
import logging
import asyncio
import argparse
import threading
import gc
import traceback
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from functools import lru_cache

# Web framework
from quart import Quart, request, jsonify

# Utilities
import aiohttp
from fake_useragent import UserAgent

# Import solver modules
try:
    from yidun_proxyless import Dun163, initialize_global_model, get_compiled_js
    SOLVER_AVAILABLE = True
    print("✅ Solver modules imported successfully")
except ImportError as e:
    print(f"⚠️ Could not import solver: {e}")
    print("⚠️ Will run in mock mode")
    SOLVER_AVAILABLE = False

# ============================================
# COLORED LOGGING (Same as Turnstile)
# ============================================

COLORS = {
    'MAGENTA': '\033[35m',
    'BLUE': '\033[34m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'RED': '\033[31m',
    'RESET': '\033[0m',
}

class CustomLogger(logging.Logger):
    """Custom logger with colored output"""
    def _format_message(self, level: str, color: str, message: str) -> str:
        timestamp = datetime.now().strftime('%H:%M:%S')
        return f"[{timestamp}] [{COLORS.get(color)}{level}{COLORS.get('RESET')}] {message}"

    def debug(self, message: str, *args, **kwargs):
        super().debug(self._format_message('DEBUG', 'MAGENTA', message), *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        super().info(self._format_message('INFO', 'BLUE', message), *args, **kwargs)

    def success(self, message: str, *args, **kwargs):
        super().info(self._format_message('SUCCESS', 'GREEN', message), *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        super().warning(self._format_message('WARNING', 'YELLOW', message), *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        super().error(self._format_message('ERROR', 'RED', message), *args, **kwargs)

# Setup logging
logging.setLoggerClass(CustomLogger)
logger = logging.getLogger("YidunAPIServer")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

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

def force_garbage_collect() -> None:
    """Force garbage collection to free memory"""
    collected = gc.collect()
    logger.debug(f"Garbage collected: {collected} objects")

# ============================================
# MOCK SOLVER (Fallback)
# ============================================

class MockDun163:
    """Mock solver for testing when real solver not available"""
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
    
    def run(self):
        """Mock run method"""
        import time
        time.sleep(1.5)
        self.resp_json2 = {
            'result': True,
            'validate': f'mock_validate_{random.randint(100000000, 999999999)}'
        }
        return True

# Choose appropriate solver
if SOLVER_AVAILABLE:
    SolverClass = Dun163
else:
    SolverClass = MockDun163
    logger.warning("⚠️ Using MOCK solver - no real captcha solving")

# ============================================
# MAIN SERVER CLASS (Like Turnstile)
# ============================================

class YidunAPIServer:
    """Yidun Captcha Solver API Server - Same style as Turnstile"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 5000, 
                 threads: int = 1, debug: bool = False):
        
        self.host = host
        self.port = port
        self.debug = debug
        self.threads = threads
        
        # Model state
        self.model = None
        self.js_ctx = None
        self.model_lock = threading.Lock()
        self.start_time = time.time()
        self.request_count = 0
        self.success_count = 0
        self.fail_count = 0
        
        # Create Quart app
        self.app = Quart(__name__)
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup API routes - Same as Turnstile"""
        self.app.before_serving(self._startup)
        self.app.route('/', methods=['GET'])(self.index)
        self.app.route('/health', methods=['GET'])(self.health)
        self.app.route('/stats', methods=['GET'])(self.stats)
        self.app.route('/solve', methods=['GET', 'POST'])(self.solve_endpoint)
        self.app.route('/memory', methods=['GET'])(self.memory_stats)
    
    async def _startup(self) -> None:
        """Initialize on startup"""
        logger.info("=" * 60)
        logger.info("🚀 YIDUN CAPTCHA SOLVER API SERVER")
        logger.info("=" * 60)
        logger.info(f"📡 Host: {self.host}")
        logger.info(f"🔌 Port: {self.port}")
        logger.info(f"🧵 Threads: {self.threads}")
        logger.info(f"🐛 Debug: {self.debug}")
        logger.info(f"🎭 Mode: {'MOCK' if not SOLVER_AVAILABLE else 'REAL'}")
        logger.info(f"💾 Memory: {get_memory_usage():.1f} MB")
        logger.info("=" * 60)
        
        # Check required files
        if SOLVER_AVAILABLE:
            required_files = ['yidun_proxyless.py', 'dun163.js', 'net.pkl']
            for file in required_files:
                if os.path.exists(file):
                    logger.success(f"✅ Found: {file}")
                else:
                    logger.error(f"❌ Missing: {file}")
            
            # Load model in background
            await self._load_model_async()
        else:
            logger.warning("⚠️ Running in MOCK MODE - no real solving")
        
        logger.success(f"✅ Server ready on http://{self.host}:{self.port}")
    
    async def _load_model_async(self) -> None:
        """Load ML model asynchronously"""
        logger.info("📥 Loading ML model (net.pkl)...")
        
        def load_sync():
            with self.model_lock:
                if self.model is None and SOLVER_AVAILABLE:
                    try:
                        # Load model
                        self.model = initialize_global_model()
                        self.js_ctx = get_compiled_js('dun163.js')
                        
                        memory = get_memory_usage()
                        logger.success(f"✅ Model loaded! Memory: {memory:.1f} MB")
                        
                        if self.model:
                            logger.success("  - ML Model: LOADED")
                        if self.js_ctx:
                            logger.success("  - JavaScript: LOADED")
                    except Exception as e:
                        logger.error(f"Failed to load model: {e}")
                        self.model = None
        
        # Run in thread pool
        await asyncio.get_event_loop().run_in_executor(None, load_sync)
    
    async def index(self):
        """Home page - HTML documentation (Like Turnstile)"""
        memory = get_memory_usage()
        uptime = time.time() - self.start_time
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
                        <h1 class="text-3xl font-bold text-center mb-2">🛡️ Yidun Captcha Solver API</h1>
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
                                <div class="text-purple-400 text-xl mb-1">{self.request_count}</div>
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
curl -X POST https://yidun-solver.railway.app/solve \\
     -H "Content-Type: application/json" \\
     -d '{{"id": "fef5c67c39074e9d845f4bf579cc07af"}}'
                            </pre>
                        </div>
                        
                        <div class="mt-6 text-center text-sm text-gray-500">
                            <p>Other endpoints: 
                                <a href="/health" class="text-blue-400 hover:underline">/health</a> | 
                                <a href="/stats" class="text-blue-400 hover:underline">/stats</a> |
                                <a href="/memory" class="text-blue-400 hover:underline">/memory</a>
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
    
    async def health(self):
        """Health check endpoint"""
        memory = get_memory_usage()
        status = 'healthy'
        if memory > 900:
            status = 'degraded'
        
        return jsonify({
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'memory_mb': round(memory, 1),
            'model_loaded': self.model is not None if SOLVER_AVAILABLE else False,
            'js_loaded': self.js_ctx is not None if SOLVER_AVAILABLE else False,
            'mock_mode': not SOLVER_AVAILABLE,
            'requests_served': self.request_count
        })
    
    async def stats(self):
        """Statistics endpoint"""
        memory = get_memory_usage()
        uptime = time.time() - self.start_time
        
        return jsonify({
            'server': {
                'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
                'uptime_seconds': round(uptime, 2),
                'uptime_human': f"{int(uptime//3600)}h {int((uptime%3600)//60)}m",
                'requests_served': self.request_count,
                'success_count': self.success_count,
                'fail_count': self.fail_count,
                'success_rate': round((self.success_count / max(self.request_count, 1)) * 100, 1)
            },
            'memory': {
                'current_mb': round(memory, 1),
                'limit_mb': 1024,
                'usage_percent': round((memory/1024)*100, 1)
            },
            'model': {
                'loaded': self.model is not None if SOLVER_AVAILABLE else False,
                'mock_mode': not SOLVER_AVAILABLE
            }
        })
    
    async def memory_stats(self):
        """Memory statistics endpoint"""
        memory = get_memory_usage()
        collected = gc.collect()
        
        return jsonify({
            'memory': {
                'current_mb': round(memory, 2),
                'limit_mb': 1024,
                'usage_percent': round((memory/1024)*100, 2)
            },
            'garbage_collector': {
                'collected': collected,
                'counts': gc.get_count()
            }
        })
    
    async def solve_endpoint(self):
        """Main solving endpoint - Like Turnstile"""
        self.request_count += 1
        req_id = self.request_count
        
        # Parse request (GET or POST)
        if request.method == 'GET':
            id_ = request.args.get('id', "fef5c67c39074e9d845f4bf579cc07af")
            referer = request.args.get('referer', "https://mtacc.mobilelegends.com/")
            fp_h = request.args.get('fp_h', "mtacc.mobilelegends.com")
            ua = request.args.get('ua')
            domain = request.args.get('domain', "https://c.dun.163.com")
        else:
            data = await request.get_json()
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
                ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        
        logger.info(f"[{req_id}] 📝 Request | ID: {id_[:16]}...")
        if self.debug:
            logger.debug(f"[{req_id}]   UA: {ua[:50]}...")
        
        start_time_req = time.time()
        
        try:
            # Create solver instance
            solver = SolverClass(
                id_=id_,
                referer=referer,
                fp_h=fp_h,
                ua=ua,
                thread_id=req_id,
                domain=domain
            )
            
            # Run solver
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, solver.run)
            elapsed = time.time() - start_time_req
            
            if success and hasattr(solver, 'resp_json2') and solver.resp_json2:
                validate = solver.resp_json2.get('validate', '')
                token = ""
                
                # Generate final token if available
                if validate and hasattr(solver, 'ctx') and solver.ctx and hasattr(solver, 'fp'):
                    try:
                        token = solver.ctx.call('do_onVerify', validate, solver.fp)
                    except Exception as e:
                        logger.error(f"[{req_id}] Token generation error: {e}")
                
                self.success_count += 1
                logger.success(f"[{req_id}] ✅ Solved in {elapsed:.2f}s | Token: {token[:30]}...")
                
                # Force garbage collection every 5 requests
                if req_id % 5 == 0:
                    force_garbage_collect()
                
                return jsonify({
                    'success': True,
                    'token': token,
                    'validate': validate,
                    'elapsed_time': round(elapsed, 3),
                    'request_id': req_id,
                    'memory_mb': round(get_memory_usage(), 1)
                })
            else:
                self.fail_count += 1
                logger.error(f"[{req_id}] ❌ Failed in {elapsed:.2f}s")
                
                return jsonify({
                    'success': False,
                    'error': 'Failed to solve captcha',
                    'elapsed_time': round(elapsed, 3),
                    'request_id': req_id
                }), 422
                
        except Exception as e:
            elapsed = time.time() - start_time_req
            self.fail_count += 1
            logger.error(f"[{req_id}] 💥 Error: {str(e)}")
            if self.debug:
                traceback.print_exc()
            
            return jsonify({
                'success': False,
                'error': str(e),
                'elapsed_time': round(elapsed, 3),
                'request_id': req_id
            }), 500

# ============================================
# COMMAND LINE ARGUMENTS
# ============================================

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Yidun Captcha Solver API Server')
    
    parser.add_argument('--host', type=str, default='127.0.0.1',
                       help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port to bind to (default: 5000)')
    parser.add_argument('--threads', type=int, default=1,
                       help='Number of threads (default: 1)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')
    
    return parser.parse_args()

# ============================================
# MAIN ENTRY POINT
# ============================================

def main():
    """Main entry point"""
    args = parse_args()
    
    # Override port with environment variable (for Railway)
    if 'PORT' in os.environ:
        args.port = int(os.environ['PORT'])
    
    # Override host for Railway
    if 'RAILWAY_ENVIRONMENT' in os.environ or 'RAILWAY_STATIC_URL' in os.environ:
        args.host = '0.0.0.0'
        logger.info("🛤️ Detected Railway.app environment")
    
    # Create and run server
    server = YidunAPIServer(
        host=args.host,
        port=args.port,
        threads=args.threads,
        debug=args.debug
    )
    
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down...")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()