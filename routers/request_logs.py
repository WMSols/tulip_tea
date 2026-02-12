"""
Request Logs Router
===================
Provides endpoint to retrieve request performance logs.
"""
from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Dict, Optional
import json
import os
from datetime import datetime

router = APIRouter(prefix="/request-logs", tags=["Request Logs", "Common APIs"])

_log_file = "requests.txt"


@router.get("/", response_model=List[Dict])
async def get_request_logs(
    limit: int = Query(100, description="Maximum number of log entries to return"),
    path: Optional[str] = Query(None, description="Filter by endpoint path"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    min_time_ms: Optional[float] = Query(None, description="Filter by minimum response time (ms)"),
    max_time_ms: Optional[float] = Query(None, description="Filter by maximum response time (ms)"),
    status_code: Optional[int] = Query(None, description="Filter by HTTP status code")
):
    """
    Get request performance logs.
    
    Returns all logged requests with timing information including:
    - Request timestamp
    - HTTP method and path
    - Response time (total, backend, Supabase)
    - Number of Supabase calls
    - Status code
    - Client IP
    
    Query Parameters:
        limit: Maximum number of entries to return (default: 100, max: 1000)
        path: Filter by endpoint path (e.g., "/shops/all")
        method: Filter by HTTP method (GET, POST, PUT, DELETE)
        min_time_ms: Minimum response time in milliseconds
        max_time_ms: Maximum response time in milliseconds
        status_code: Filter by HTTP status code
    
    Example:
        GET /request-logs/?limit=50&path=/shops/all&min_time_ms=100
    """
    if not os.path.exists(_log_file):
        return []
    
    if limit > 1000:
        limit = 1000
    
    try:
        logs = []
        with open(_log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    log_entry = json.loads(line.strip())
                    logs.append(log_entry)
                except json.JSONDecodeError:
                    continue
        
        # Apply filters
        filtered_logs = logs
        if path:
            filtered_logs = [log for log in filtered_logs if path.lower() in log.get('path', '').lower()]
        if method:
            filtered_logs = [log for log in filtered_logs if log.get('method', '').upper() == method.upper()]
        if min_time_ms is not None:
            filtered_logs = [log for log in filtered_logs if log.get('response_time_ms', 0) >= min_time_ms]
        if max_time_ms is not None:
            filtered_logs = [log for log in filtered_logs if log.get('response_time_ms', 0) <= max_time_ms]
        if status_code:
            filtered_logs = [log for log in filtered_logs if log.get('status_code') == status_code]
        
        # Sort by timestamp (newest first) and limit
        filtered_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return filtered_logs[:limit]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading log file: {str(e)}"
        )


@router.get("/stats", response_model=Dict)
async def get_request_stats():
    """
    Get aggregated statistics from request logs.
    
    Returns:
        - Total requests
        - Average response time
        - Average Supabase time
        - Average backend time
        - Slowest endpoints
        - Most called endpoints
        - Error rate
    """
    if not os.path.exists(_log_file):
        return {
            "total_requests": 0,
            "message": "No logs available"
        }
    
    try:
        logs = []
        with open(_log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    log_entry = json.loads(line.strip())
                    logs.append(log_entry)
                except json.JSONDecodeError:
                    continue
        
        if not logs:
            return {
                "total_requests": 0,
                "message": "No log entries found"
            }
        
        # Calculate statistics
        total_requests = len(logs)
        total_response_time = sum(log.get('response_time_ms', 0) for log in logs)
        total_supabase_time = sum(log.get('supabase_total_time_ms', 0) for log in logs)
        total_backend_time = sum(log.get('backend_time_ms', 0) for log in logs)
        
        avg_response_time = total_response_time / total_requests if total_requests > 0 else 0
        avg_supabase_time = total_supabase_time / total_requests if total_requests > 0 else 0
        avg_backend_time = total_backend_time / total_requests if total_requests > 0 else 0
        
        # Count errors
        error_count = sum(1 for log in logs if log.get('status_code', 200) >= 400)
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        
        # Most called endpoints
        endpoint_counts = {}
        for log in logs:
            path = log.get('path', 'unknown')
            endpoint_counts[path] = endpoint_counts.get(path, 0) + 1
        
        most_called = sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Slowest endpoints (average time per endpoint)
        endpoint_times = {}
        endpoint_counts_for_avg = {}
        for log in logs:
            path = log.get('path', 'unknown')
            time_ms = log.get('response_time_ms', 0)
            if path not in endpoint_times:
                endpoint_times[path] = 0
                endpoint_counts_for_avg[path] = 0
            endpoint_times[path] += time_ms
            endpoint_counts_for_avg[path] += 1
        
        slowest_endpoints = []
        for path, total_time in endpoint_times.items():
            count = endpoint_counts_for_avg[path]
            avg_time = total_time / count if count > 0 else 0
            slowest_endpoints.append({
                "path": path,
                "avg_time_ms": round(avg_time, 2),
                "count": count
            })
        slowest_endpoints.sort(key=lambda x: x['avg_time_ms'], reverse=True)
        slowest_endpoints = slowest_endpoints[:10]
        
        return {
            "total_requests": total_requests,
            "average_response_time_ms": round(avg_response_time, 2),
            "average_supabase_time_ms": round(avg_supabase_time, 2),
            "average_backend_time_ms": round(avg_backend_time, 2),
            "error_count": error_count,
            "error_rate_percent": round(error_rate, 2),
            "most_called_endpoints": [
                {"path": path, "count": count} for path, count in most_called
            ],
            "slowest_endpoints": slowest_endpoints
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating statistics: {str(e)}"
        )


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_request_logs():
    """
    Clear all request logs.
    
    WARNING: This will delete all logged request data.
    """
    try:
        if os.path.exists(_log_file):
            os.remove(_log_file)
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing log file: {str(e)}"
        )

