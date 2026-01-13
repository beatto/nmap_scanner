from flask import Flask, render_template, request, jsonify, Response
import scanner_core
import database
import csv
import io

app = Flask(__name__)

# Initialize database
database.init_db()

@app.route('/')
def index():
    return render_template('index.html')

import json
import time

@app.route('/api/scan', methods=['POST'])
def scan():
    data = request.json
    target = data.get('target')
    if not target:
        return jsonify({"status": "error", "message": "No target specified"}), 400

    def generate():
        all_hosts_data = []
        try:
            for event in scanner_core.run_nmap_scan(target):
                if event["type"] == "host_result":
                    all_hosts_data.append(event["data"])
                
                # Forward event to SSE stream
                yield f"data: {json.dumps(event)}\n\n"

            # After generator finishes, save everything to DB if we have data
            if all_hosts_data:
                database.add_scan(target, all_hosts_data)
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Stream Error: {str(e)}'})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/history', methods=['GET'])
def history():
    try:
        data = database.get_history()
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": f"DB Error: {str(e)}"}), 500

@app.route('/api/export/csv/<int:scan_id>')
def export_csv(scan_id):
    try:
        scan = database.get_scan_by_id(scan_id)
        if not scan:
            return "Scan not found", 404
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Target', 'Timestamp', 'Host', 'Hostname', 'State', 'Protocol', 'Port', 'Port State', 'Service', 'Version'])
        
        for host_info in scan['results']:
            for proto_info in host_info['protocols']:
                for port_info in proto_info['ports']:
                    writer.writerow([
                        scan['target'],
                        scan['timestamp'],
                        host_info['host'],
                        host_info['hostname'],
                        host_info['state'],
                        proto_info['protocol'],
                        port_info['port'],
                        port_info['state'],
                        port_info['service'],
                        port_info['version']
                    ])
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=scan_{scan_id}.csv"}
        )
    except Exception as e:
        return str(e), 500

@app.route('/api/history/<int:scan_id>', methods=['DELETE'])
def delete_history_item(scan_id):
    try:
        database.delete_scan(scan_id)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Delete Error: {str(e)}"}), 500

if __name__ == '__main__':
    # Running on 127.0.0.1:5000 by default
    app.run(debug=True)
