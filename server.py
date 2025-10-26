from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import threading
from datetime import datetime
from collections import deque
import os

# Optional Discord bot integration
try:
    from discord_bot_http import start_discord_bot_background, discord_stats
    DISCORD_BOT_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Discord bot not available: {e}")
    DISCORD_BOT_AVAILABLE = False
    discord_stats = {
        'servers_processed': 0,
        'servers_sent': 0,
        'servers_filtered': 0,
        'unique_servers': set(),
        'last_server': None,
        'bot_connected': False,
        'bot_status': 'Not Available'
    }

app = Flask(__name__)
CORS(app)

# Queue for Roblox server info
server_queue = deque(maxlen=200)  # increased maxlen to hold more servers
ping_logs = deque(maxlen=50)

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        'status': 'online',
        'queue_size': len(server_queue),
        'timestamp': datetime.now().isoformat()
    })

# Push server info to queue
@app.route('/api/server/push', methods=['POST'])
def push_server():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        server_data = {
            'name': data.get('name'),
            'money': data.get('money'),
            'players': data.get('players'),
            'job_id': data.get('job_id'),
            'script': data.get('script'),
            'join_link': data.get('join_link'),
            'is_10m_plus': data.get('is_10m_plus', False),
            'timestamp': datetime.now().isoformat()
        }
        
        server_queue.append(server_data)
        
        return jsonify({
            'success': True,
            'message': 'Server added to queue',
            'queue_size': len(server_queue)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Pull server info without removing from queue
@app.route('/api/server/pull', methods=['GET'])
def pull_server():
    try:
        if len(server_queue) == 0:
            return jsonify({'status': 'success', 'data': None, 'queue_size': 0})
        
        server_data = server_queue.popleft()
        
        return jsonify({
            'status': 'success',
            'data': server_data,
            'queue_size': len(server_queue)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# Return all servers (same as pull)
@app.route('/api/server/all', methods=['GET'])
def all_servers():
    return jsonify({'status': 'success', 'data': list(server_queue), 'queue_size': len(server_queue)})

# Categorize servers by money
@app.route('/api/server/categories', methods=['GET'])
def get_server_categories():
    categories = {
        "1m-10m": [],
        "10m-100m": [],
        "100m+": []
    }

    for server in list(server_queue):
        try:
            money_str = str(server.get('money', '0')).lower().replace('$', '').strip()
            if money_str.endswith('m'):
                money = float(money_str[:-1]) * 1_000_000
            elif money_str.endswith('k'):
                money = float(money_str[:-1]) * 1_000
            else:
                money = float(money_str)
        except:
            money = 0

        if 1_000_000 <= money < 10_000_000:
            categories["1m-10m"].append(server)
        elif 10_000_000 <= money < 100_000_000:
            categories["10m-100m"].append(server)
        elif money >= 100_000_000:
            categories["100m+"].append(server)

    return jsonify({
        'success': True,
        'categories': categories,
        'timestamp': datetime.now().isoformat()
    })

# Optional ping endpoint
@app.route('/api/ping', methods=['POST'])
def ping():
    data = request.json or {}
    ping_entry = {'source': data.get('source', 'unknown'), 'timestamp': datetime.now().isoformat()}
    ping_logs.append(ping_entry)
    return jsonify({'success': True, 'timestamp': ping_entry['timestamp']})

# View ping logs
@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify({'logs': list(ping_logs), 'count': len(ping_logs)})

# Discord stats (optional)
@app.route('/api/discord/stats', methods=['GET'])
def get_discord_stats():
    stats_copy = discord_stats.copy()
    stats_copy['unique_servers'] = len(discord_stats['unique_servers'])
    return jsonify({'success': True, 'stats': stats_copy})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8888))
    print(f"🚀 Starting Flask server on 127.0.0.1:{port}")
    
    if DISCORD_BOT_AVAILABLE and os.environ.get('DISCORD_TOKEN'):
        try:
            discord_bot_thread = threading.Thread(target=start_discord_bot_background, daemon=True)
            discord_bot_thread.start()
            print("✅ Discord bot started in background")
        except Exception as e:
            print(f"⚠️ Discord bot not started: {e}")
    else:
        if not os.environ.get('DISCORD_TOKEN'):
            print("⚠️ DISCORD_TOKEN not found")
        print("ℹ️ Discord bot monitoring disabled")
    
    app.run(host='0.0.0.0', port=port, debug=False)
