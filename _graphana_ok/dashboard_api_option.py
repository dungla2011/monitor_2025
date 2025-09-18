#!/usr/bin/env python3
"""
Simple API server để cung cấp metrics cho dashboard
"""
from flask import Flask, jsonify, render_template_string
import asyncpg
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Database config
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'database': os.getenv('POSTGRES_DATABASE', 'postgres'),
}

TIMESCALE_SCHEMA = os.getenv('TIMESCALEDB_SCHEMA', 'glx_monitor_v2')

async def get_db_connection():
    """Get database connection"""
    return await asyncpg.connect(**DB_CONFIG)

@app.route('/api/metrics')
async def get_metrics():
    """Get current monitoring metrics"""
    try:
        conn = await get_db_connection()
        
        # Query metrics from last 24 hours
        queries = {
            'total_monitors': f"""
                SELECT COUNT(DISTINCT monitor_id) as count
                FROM {TIMESCALE_SCHEMA}.monitor_checks 
                WHERE time >= NOW() - INTERVAL '24 hours'
            """,
            'success_rate': f"""
                SELECT 
                    (COUNT(*) FILTER (WHERE status = 1)::decimal / COUNT(*) * 100) as rate
                FROM {TIMESCALE_SCHEMA}.monitor_checks 
                WHERE time >= NOW() - INTERVAL '1 hour'
            """,
            'avg_response': f"""
                SELECT AVG(response_time) as avg_time
                FROM {TIMESCALE_SCHEMA}.monitor_checks 
                WHERE time >= NOW() - INTERVAL '1 hour' AND status = 1
            """,
            'internet_status': f"""
                SELECT AVG(value) > 0.5 as online
                FROM {TIMESCALE_SCHEMA}.monitor_system_metrics 
                WHERE time >= NOW() - INTERVAL '5 minutes'
                  AND metric_type = 'internet_connectivity'
            """
        }
        
        results = {}
        for key, query in queries.items():
            row = await conn.fetchrow(query)
            if key == 'total_monitors':
                results[key] = row['count'] if row else 0
            elif key == 'success_rate':
                results[key] = float(row['rate']) if row and row['rate'] else 0.0
            elif key == 'avg_response':
                results[key] = float(row['avg_time']) if row and row['avg_time'] else 0.0
            elif key == 'internet_status':
                results[key] = bool(row['online']) if row else False
        
        await conn.close()
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent-checks')
async def get_recent_checks():
    """Get recent check results"""
    try:
        conn = await get_db_connection()
        
        query = f"""
            SELECT 
                time,
                monitor_id,
                check_type,
                status,
                response_time,
                message
            FROM {TIMESCALE_SCHEMA}.monitor_checks 
            WHERE time >= NOW() - INTERVAL '1 hour'
            ORDER BY time DESC
            LIMIT 50
        """
        
        rows = await conn.fetch(query)
        results = []
        
        for row in rows:
            results.append({
                'time': row['time'].isoformat(),
                'monitor_id': row['monitor_id'],
                'check_type': row['check_type'],
                'status': 'UP' if row['status'] == 1 else 'DOWN',
                'response_time': float(row['response_time']) if row['response_time'] else None,
                'message': row['message']
            })
        
        await conn.close()
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def dashboard():
    """Serve dashboard HTML"""
    with open('dashboard_embed.html', 'r', encoding='utf-8') as f:
        return f.read()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)