import nmap
import os
import sys

# Add Nmap to PATH explicitly for Windows if installed in common location
nmap_path = r"C:\Program Files (x86)\Nmap"
if os.path.exists(nmap_path) and nmap_path not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + nmap_path

def run_nmap_scan(target_ip):
    nm = nmap.PortScanner()
    try:
        yield {"type": "status", "message": "Discovering active hosts..."}
        
        # Phase 1: Enhanced Discovery Scan with Forced DNS Resolution
        # -sn: Ping scan
        # -PE, -PS, -PA: Multiple discovery probes
        # -R: Force reverse DNS resolution for all targets
        nm.scan(hosts=target_ip, arguments='-sn -PE -PS22,80,443,3389 -PA80,443 -R')
        active_hosts = nm.all_hosts()
        
        if not active_hosts:
            yield {"type": "status", "message": "No active hosts found."}
            return

        yield {"type": "status", "message": f"Found {len(active_hosts)} active hosts. Starting detailed scans..."}
        
        for i, host in enumerate(active_hosts):
            yield {"type": "status", "message": f"[{i+1}/{len(active_hosts)}] Scanning {host}..."}
            
            # Phase 2: Detailed scan per host
            # -Pn: Skip discovery
            # -sV: Service version detection
            # -R: Ensure resolution is tried here too
            host_nm = nmap.PortScanner()
            
            # Helper to get best hostname
            def get_best_hostname(nmap_obj, h):
                if h not in nmap_obj.all_hosts(): return ""
                # Try specific hostname first, then general
                name = nmap_obj[h].hostname()
                if not name:
                    hostnames = nmap_obj[h].get('hostnames', [])
                    for hn in hostnames:
                        if hn.get('name'):
                            return hn['name']
                return name

            # Prepare basic host info as fallback
            host_info = {
                "host": host,
                "hostname": get_best_hostname(nm, host),
                "state": "up", # From Phase 1
                "protocols": []
            }

            try:
                host_nm.scan(host, arguments='-sV -T4 -Pn -R')
                
                if host in host_nm.all_hosts():
                    host_info["hostname"] = get_best_hostname(host_nm, host) or host_info["hostname"]
                    host_info["state"] = host_nm[host].state()
                    
                    for proto in host_nm[host].all_protocols():
                        proto_info = {"protocol": proto, "ports": []}
                        for port in sorted(host_nm[host][proto].keys()):
                            port_data = host_nm[host][proto][port]
                            proto_info["ports"].append({
                                "port": port,
                                "state": port_data['state'],
                                "service": port_data['name'],
                                "version": (port_data.get('product', '') + " " + port_data.get('version', '')).strip()
                            })
                        host_info["protocols"].append(proto_info)
            except Exception as e:
                # Log error for this specific host but don't stop the whole scan
                yield {"type": "status", "message": f"Warning: Detailed scan failed for {host}: {str(e)}"}
            
            # ALWAYS yield the host result even if no ports found
            yield {"type": "host_result", "data": host_info}

        yield {"type": "status", "message": "Scan completed."}
    except Exception as e:
        yield {"type": "error", "message": str(e)}
