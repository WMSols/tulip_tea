"""
Request Logger Middleware
=========================
Tracks all incoming requests, response times, and external API calls (Supabase).
Logs data to a local file 'requests.txt' for analysis.
"""
import time
import json
import os
from datetime import datetime
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import threading

# Thread-safe file writing
_log_lock = threading.Lock()
_log_file = "requests.txt"
_max_log_entries = 10000  # Keep last 10k entries


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests with timing information."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._supabase_times = {}  # Track Supabase call times per request
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log timing information."""
        # Start timing
        start_time = time.time()
        
        # Get request details
        method = request.method
        url = str(request.url)
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        
        # Track Supabase calls for this request
        supabase_calls = []
        supabase_total_time = 0.0
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # Get response status
            status_code = response.status_code
            
            # Get Supabase timing from thread-local storage
            try:
                import threading
                thread = threading.current_thread()
                if hasattr(thread, 'supabase_calls') and thread.supabase_calls:
                    supabase_calls = thread.supabase_calls
                    supabase_total_time = sum(call.get('time_ms', 0) for call in supabase_calls)
                    # Clear for next request
                    thread.supabase_calls = []
            except:
                pass
            
            # Log the request
            self._log_request(
                timestamp=datetime.now().isoformat(),
                method=method,
                path=path,
                url=url,
                status_code=status_code,
                response_time_ms=response_time_ms,
                supabase_calls=len(supabase_calls),
                supabase_total_time_ms=supabase_total_time,
                client_ip=client_ip
            )
            
            return response
            
        except Exception as e:
            # Log error
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            self._log_request(
                timestamp=datetime.now().isoformat(),
                method=method,
                path=path,
                url=url,
                status_code=500,
                response_time_ms=response_time_ms,
                supabase_calls=0,
                supabase_total_time_ms=0.0,
                client_ip=client_ip,
                error=str(e)
            )
            raise
    
    def _log_request(
        self,
        timestamp: str,
        method: str,
        path: str,
        url: str,
        status_code: int,
        response_time_ms: float,
        supabase_calls: int,
        supabase_total_time_ms: float,
        client_ip: str,
        error: str = None
    ):
        """Write request log to file."""
        log_entry = {
            "timestamp": timestamp,
            "method": method,
            "path": path,
            "url": url,
            "status_code": status_code,
            "response_time_ms": round(response_time_ms, 2),
            "supabase_calls": supabase_calls,
            "supabase_total_time_ms": round(supabase_total_time_ms, 2),
            "backend_time_ms": round(response_time_ms - supabase_total_time_ms, 2),
            "client_ip": client_ip,
            "error": error
        }
        
        # Thread-safe file writing
        with _log_lock:
            try:
                # Append to file
                with open(_log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry) + '\n')
                
                # Rotate file if too large (keep last N entries)
                self._rotate_log_file()
            except Exception as e:
                # Don't fail request if logging fails
                print(f"Warning: Failed to log request: {e}")
    
    def _rotate_log_file(self):
        """Keep only the last N log entries."""
        try:
            if not os.path.exists(_log_file):
                return
            
            # Check file size (rough estimate: 200 bytes per entry)
            file_size = os.path.getsize(_log_file)
            if file_size < _max_log_entries * 200:
                return  # File not too large yet
            
            # Read all lines
            with open(_log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Keep only last N entries
            if len(lines) > _max_log_entries:
                lines = lines[-_max_log_entries:]
                
                # Write back
                with open(_log_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
        except Exception as e:
            print(f"Warning: Failed to rotate log file: {e}")


def track_supabase_call(request: Request, operation: str, time_ms: float):
    """Track a Supabase API call for the current request."""
    if not hasattr(request.state, 'supabase_calls'):
        request.state.supabase_calls = []
    
    request.state.supabase_calls.append({
        "operation": operation,
        "time_ms": round(time_ms, 2)
    })

