import requests
import yaml
import logging
import socket
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SS_CONFIG_URLS = [
    "https://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-1.csv",
    "https://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-2.csv",
    "https://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-3.csv",
    "https://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-4.csv",
]

def clean_ss_link(ss_link: str) -> str:
    """
    Remove trailing URL query or fragments from ss link, e.g. remove /?POST%20
    """
    if "/?" in ss_link:
        ss_link = ss_link.split("/?")[0]
    elif "?" in ss_link:
        ss_link = ss_link.split("?")[0]
    return ss_link

def parse_ss_link(ss_link: str):
    """
    Parses a ShadowSocks ss:// link of the form:
    ss://base64encoded@server:port
    Returns dict with keys: server, port, cipher, password
    """
    ss_link = clean_ss_link(ss_link)
    if not ss_link.startswith("ss://"):
        raise ValueError("Invalid ss link, must start with ss://")
    # Remove prefix
    raw = ss_link[5:]
    
    # Sometimes link can be user:pass@host:port or base64@host:port
    # But here format is base64@host:port
    try:
        userinfo, server_part = raw.split("@")
    except ValueError:
        raise ValueError("ss link missing '@' separator")
    
    try:
        server, port_str = server_part.split(":")
    except ValueError:
        raise ValueError("ss link missing ':' port separator")
    
    port = int(port_str)
    
    import base64
    # base64 decode userinfo to get cipher:password
    padding = '=' * (-len(userinfo) % 4)  # fix padding
    decoded = base64.urlsafe_b64decode(userinfo + padding).decode('utf-8')
    # format is cipher:password
    try:
        cipher, password = decoded.split(":", 1)
    except ValueError:
        raise ValueError("decoded userinfo does not contain ':'")
    
    return {
        "server": server,
        "port": port,
        "cipher": cipher,
        "password": password,
    }

def resolve_ip(server: str) -> str:
    try:
        ip = socket.gethostbyname(server)
        return ip
    except Exception as e:
        logging.warning(f"Failed to resolve {server}: {e}")
        return None

def fetch_ss_links(url: str):
    """
    Download CSV file from URL, extract ss links
    """
    logging.info(f"Fetching config from: {url}")
    resp = requests.get(url)
    resp.raise_for_status()
    text = resp.text
    # Extract ss links: assume one per line or comma separated or at least containing ss://
    ss_links = []
    for line in text.splitlines():
        if "ss://" in line:
            # line might have other stuff, extract ss://... part until space
            start = line.find("ss://")
            part = line[start:].split()[0]
            ss_links.append(part)
    logging.info(f"Found {len(ss_links)} ss links in {url}")
    return ss_links

def build_clash_config(proxies):
    proxy_entries = []
    for i, p in enumerate(proxies, start=1):
        entry = {
            "name": f"Server-{i}",
            "type": "ss",
            "server": p["ip"],
            "port": p["port"],
            "cipher": p["cipher"],
            "password": p["password"],
            "udp": True,
        }
        proxy_entries.append(entry)
    
    config = {
        "proxies": proxy_entries,
        "proxy-groups": [
            {
                "name": "Auto",
                "type": "url-test",
                "proxies": [f"Server-{i}" for i in range(1, len(proxy_entries)+1)],
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
            }
        ],
        "rules": ["MATCH,Auto"],
    }
    return config

def main():
    all_proxies = []
    for url in SS_CONFIG_URLS:
        try:
            ss_links = fetch_ss_links(url)
            for ss_link in ss_links:
                try:
                    parsed = parse_ss_link(ss_link)
                    ip = resolve_ip(parsed["server"])
                    if ip:
                        all_proxies.append({
                            "ip": ip,
                            "port": parsed["port"],
                            "cipher": parsed["cipher"],
                            "password": parsed["password"],
                        })
                except Exception as e:
                    logging.error(f"Error parsing ss link {ss_link}: {e}")
        except Exception as e:
            logging.warning(f"Skipping URL {url} due to fetch failure: {e}")

    # Take unique proxies by IP and port (avoid duplicates)
    unique = {}
    for p in all_proxies:
        key = (p["ip"], p["port"])
        if key not in unique:
            unique[key] = p
    unique_proxies = list(unique.values())

    # We want exactly 4 proxies max
    proxies = unique_proxies[:4]

    if len(proxies) < 4:
        logging.error(f"Only found {len(proxies)} valid proxies, need 4 to proceed. Creating empty config file.")
        config = {
            "proxies": [],
            "proxy-groups": [
                {
                    "name": "Auto",
                    "type": "url-test",
                    "proxies": [],
                    "url": "http://www.gstatic.com/generate_204",
                    "interval": 300,
                }
            ],
            "rules": ["MATCH,Auto"],
        }
    else:
        config = build_clash_config(proxies)

    with open("ProjectAinita_Clash.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, sort_keys=False, allow_unicode=True)

    logging.info(f"Output file created with {len(proxies)} proxies.")

if __name__ == "__main__":
    main()
