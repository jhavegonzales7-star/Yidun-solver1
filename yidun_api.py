#!/usr/bin/env python3
import os
import sys
import json
import time
import uuid
import random
import string
import asyncio
import threading
import warnings
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from quart import Quart, request, jsonify

import requests
import execjs
import cv2
import numpy as np
import torch
import torch.nn as nn
from collections import OrderedDict
from loguru import logger
from fake_useragent import UserAgent

warnings.filterwarnings("ignore")

# ============================================
# COLOR LOGGING (like Turnstile solver)
# ============================================
COLORS = {
    'MAGENTA': '\033[35m',
    'BLUE': '\033[34m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'RED': '\033[31m',
    'RESET': '\033[0m',
}

# ============================================
# RAILWAY OPTIMIZATIONS
# ============================================
IS_RAILWAY = 'RAILWAY_ENVIRONMENT' in os.environ or 'RAILWAY_STATIC_URL' in os.environ

if IS_RAILWAY:
    print(f"{COLORS['BLUE']}🛤️ Running on Railway - applying optimizations{COLORS['RESET']}")
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    os.environ['OMP_NUM_THREADS'] = '2'
    os.environ['MKL_NUM_THREADS'] = '2'
    torch.set_num_threads(2)
    torch.set_grad_enabled(False)
    try:
        cv2.setNumThreads(1)
    except:
        pass
    DIR_PATH = '/app'
    TOKEN_OUTPUT_FILE = '/tmp/validated_tokens.txt'
else:
    DIR_PATH = os.path.dirname(os.path.abspath(__file__))
    TOKEN_OUTPUT_FILE = os.path.join(DIR_PATH, 'validated_tokens.txt')

# ============================================
# CONSTANTS
# ============================================
REFERER = "https://mtacc.mobilelegends.com/"
ID = "fef5c67c39074e9d845f4bf579cc07af"
FP_H = "mtacc.mobilelegends.com"
DUN163_DOMAINS = [
    "https://c.dun.163.com",
    "https://c.dun.163yun.com"
]

# ============================================
# MODEL & JS LOADING (from your original code)
# ============================================
_model_state = None
_model_lock = threading.Lock()
_js_ctx = None
_js_lock = threading.Lock()

def get_compiled_js():
    global _js_ctx
    if _js_ctx is not None:
        return _js_ctx
    
    with _js_lock:
        if _js_ctx is not None:
            return _js_ctx
        
        js_path = os.path.join(DIR_PATH, 'dun163.js')
        if not os.path.exists(js_path):
            logger.error(f"JS file not found at {js_path}")
            return None
        
        try:
            with open(js_path, 'r', encoding='utf-8') as f:
                js_code = f.read()
            _js_ctx = execjs.compile(js_code)
            logger.success("JavaScript loaded successfully")
            return _js_ctx
        except Exception as e:
            logger.error(f"Failed to load JS: {e}")
            return None

def initialize_global_model():
    global _model_state
    
    if _model_state is not None:
        return _model_state
        
    with _model_lock:
        if _model_state is not None:
            return _model_state
            
        model_path = os.path.join(DIR_PATH, 'net.pkl')
        if not os.path.exists(model_path):
            logger.error(f"Model file not found at {model_path}")
            return None
            
        try:
            state = torch.load(model_path, map_location=torch.device('cpu'), weights_only=False)
            if 'net' in state:
                state['net'] = state['net'].to('cpu')
                state['net'].eval()
            _model_state = state
            logger.success("Model loaded successfully")
            return _model_state
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return None

# ============================================
# YOUR EXISTING FUNCTIONS (copy all of them here)
# ============================================
# Copy all your existing functions from yidun_proxyless.py:
# - rotate_about_center
# - parse_y_pred
# - Mini class
# - get_clz_rect_from_image
# - get_cut_img
# - get_flags_rects_from_image
# - Dun163 class
# - emergency functions

# [PASTE ALL YOUR EXISTING FUNCTIONS HERE]
# For brevity, I'll summarize but you need to copy them from your yidun_proxyless.py

# ============================================
# YIDUN API SERVER CLASS (like Turnstile solver)
# ============================================
class YidunAPIServer:
    def __init__(self, debug: bool = False, thread_count: int = 3):
        self.app = Quart(__name__)
        self.debug = debug
        self.thread_count = thread_count
        self.solver_pool = asyncio.Queue()
        self._setup_routes()
        
        # Initialize resources
        self.js_ctx = get_compiled_js()
        self.model_state = initialize_global_model()
        
    def _setup_routes(self):
        """Set up API routes."""
        self.app.before_serving(self._startup)
        self.app.route('/solve', methods=['GET', 'POST'])(self.solve_captcha)
        self.app.route('/health', methods=['GET'])(self.health_check)
        self.app.route('/', methods=['GET'])(self.index)
        
    async def _startup(self):
        """Initialize solver pool on startup."""
        logger.info("Initializing Yidun solver pool...")
        for i in range(self.thread_count):
            await self.solver_pool.put(i + 1)
        logger.success(f"Solver pool initialized with {self.thread_count} threads")
        
    async def solve_captcha(self):
        """Main API endpoint to solve Yidun captcha."""
        # Get parameters
        if request.method == 'POST':
            data = await request.get_json()
            image_url = data.get('image_url')
            token = data.get('token')
            captcha_type = data.get('type', 7)
        else:
            image_url = request.args.get('image_url')
            token = request.args.get('token')
            captcha_type = request.args.get('type', 7, type=int)
        
        if not image_url:
            return jsonify({
                "status": "error",
                "error": "image_url is required"
            }), 400
        
        thread_id = await self.solver_pool.get()
        start_time = time.time()
        
        try:
            if self.debug:
                logger.debug(f"Thread {thread_id}: Solving captcha for URL: {image_url[:50]}...")
            
            # Create solver instance
            solver = Dun163(
                id_=ID,
                referer=REFERER,
                fp_h=FP_H,
                ua=UserAgent().random,
                thread_id=thread_id
            )
            
            # Solve the captcha
            if captcha_type == 7:
                click_points, img_time = solver.handle_click_captcha_hybrid(image_url, token or "dummy", 0)
                
                # Generate response data
                result = {
                    "status": "success",
                    "click_points": click_points,
                    "coordinates": [
                        {"x": p["x"], "y": p["y"]} for p in click_points
                    ],
                    "elapsed_time": round(time.time() - start_time, 3)
                }
                
                if self.debug:
                    logger.success(f"Thread {thread_id}: Solved in {result['elapsed_time']}s")
                
                return jsonify(result)
            else:
                return jsonify({
                    "status": "error",
                    "error": f"Unsupported captcha type: {captcha_type}"
                }), 400
                
        except Exception as e:
            elapsed = round(time.time() - start_time, 3)
            logger.error(f"Thread {thread_id}: Error: {str(e)}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "elapsed_time": elapsed
            }), 500
            
        finally:
            await self.solver_pool.put(thread_id)
    
    async def health_check(self):
        """Health check endpoint."""
        pool_size = self.solver_pool.qsize()
        return jsonify({
            "status": "healthy",
            "pool_size": pool_size,
            "model_loaded": self.model_state is not None,
            "js_loaded": self.js_ctx is not None,
            "timestamp": datetime.now().isoformat()
        })
    
    async def index(self):
        """API documentation page."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Yidun Solver API</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-900 text-gray-200 min-h-screen flex items-center justify-center">
            <div class="bg-gray-800 p-8 rounded-lg shadow-md max-w-3xl w-full border border-blue-500">
                <h1 class="text-3xl font-bold mb-6 text-center text-blue-500">Yidun Solver API</h1>
                
                <p class="mb-4 text-gray-300">API for solving Yidun (Netease) captcha challenges.</p>
                
                <h2 class="text-xl font-semibold mt-6 mb-3 text-blue-400">Endpoints:</h2>
                
                <div class="bg-gray-700 p-4 rounded-lg mb-4">
                    <h3 class="text-lg font-semibold text-blue-300">GET /solve</h3>
                    <p class="text-sm text-gray-400 mb-2">Solve click captcha (type 7)</p>
                    <p class="text-sm"><span class="text-yellow-400">Parameters:</span></p>
                    <ul class="list-disc pl-6 text-sm text-gray-300">
                        <li><span class="text-green-400">image_url</span> (required) - URL of the captcha background image</li>
                        <li><span class="text-green-400">token</span> (optional) - Captcha token</li>
                        <li><span class="text-green-400">type</span> (optional) - Captcha type (default: 7)</li>
                    </ul>
                    <p class="text-sm mt-2"><span class="text-yellow-400">Example:</span></p>
                    <code class="text-xs break-all text-blue-300">/solve?image_url=https://example.com/bg.jpg&type=7</code>
                </div>
                
                <div class="bg-gray-700 p-4 rounded-lg mb-4">
                    <h3 class="text-lg font-semibold text-blue-300">POST /solve</h3>
                    <p class="text-sm text-gray-400 mb-2">JSON payload:</p>
                    <pre class="text-xs bg-gray-900 p-2 rounded overflow-x-auto">
{
    "image_url": "https://...",
    "token": "optional_token",
    "type": 7
}
                    </pre>
                </div>
                
                <div class="bg-gray-700 p-4 rounded-lg mb-4">
                    <h3 class="text-lg font-semibold text-blue-300">GET /health</h3>
                    <p class="text-sm text-gray-400">Check API health and status</p>
                </div>
                
                <h2 class="text-xl font-semibold mt-6 mb-3 text-blue-400">Response Format:</h2>
                <pre class="text-xs bg-gray-900 p-2 rounded overflow-x-auto">
{
    "status": "success",
    "click_points": [{"x": 123, "y": 45}, ...],
    "coordinates": [[123, 45], ...],
    "elapsed_time": 1.234
}
                </pre>
                
                <div class="bg-blue-900 border-l-4 border-blue-600 p-4 mt-6">
                    <p class="text-blue-200">Deployed on Railway.app 🚀</p>
                </div>
            </div>
        </body>
        </html>
        """

def create_app(debug: bool = False, threads: int = 3):
    """Create and configure the Quart app."""
    server = YidunAPIServer(debug=debug, thread_count=threads)
    return server.app

# ============================================
# MAIN ENTRY POINT
# ============================================
def parse_args():
    parser = argparse.ArgumentParser(description="Yidun Solver API Server")
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--threads', type=int, default=3, help='Number of solver threads')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    
    # Remove default logger and add custom
    logger.remove()
    logger.add(lambda msg: print(msg, end=''), format="{time:HH:mm:ss} | {level: <8} | {message}")
    
    print(f"\n{COLORS['BLUE']}{'='*50}{COLORS['RESET']}")
    print(f"{COLORS['GREEN']}YIDUN SOLVER API - RAILWAY EDITION{COLORS['RESET']}")
    print(f"{COLORS['BLUE']}{'='*50}{COLORS['RESET']}\n")
    
    # Initialize resources
    js_ctx = get_compiled_js()
    model_state = initialize_global_model()
    
    if not js_ctx or not model_state:
        print(f"{COLORS['RED']}Failed to initialize required resources!{COLORS['RESET']}")
        sys.exit(1)
    
    # Create and run app
    app = create_app(debug=args.debug, threads=args.threads)
    
    print(f"{COLORS['YELLOW']}Starting server on {args.host}:{args.port}{COLORS['RESET']}")
    print(f"{COLORS['YELLOW']}Debug mode: {args.debug}{COLORS['RESET']}")
    print(f"{COLORS['YELLOW']}Threads: {args.threads}{COLORS['RESET']}\n")
    
    app.run(host=args.host, port=args.port)