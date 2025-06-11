import requests
import base64
import logging
import socket
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_config(url, server_number):
    https_url = url.replace('ssconf://', 'https://')
    try:
        response = requests.get(https_url, timeout=10)
        response.raise_for_status()
        content = response.text.strip()
        if content.startswith('ss://'):
            content = f"{content}#Server-{server_number}"
            return content
        else:
            logger.error(f"Invalid config format from {https_url}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {https_url}: {str(e)}")
        return None

def parse_ss_link(ss_link):
    parts = ss_link.split('#')
    tag = parts[1] if len(parts) > 1 else "Unnamed"
    link_body = parts[0][5:]

    if '@' in link_body:
        userinfo, hostport = link_body.split('@', 1)
        try:
            padding = '=' * ((4 - len(userinfo) % 4) % 4)
            decoded = base64.urlsafe_b64decode(userinfo + padding).decode()
        except Exception:
            decoded = userinfo

        if ':' in decoded:
            cipher, password = decoded.split(':', 1)
        else:
            cipher = decoded
            password = ""

        if ':' in hostport:
            server, port = hostport.split(':', 1)
        else:
            server, port = hostport, "0"

        return {
            "name": tag,
            "type": "ss",
            "cipher": cipher,
            "password": password,
            "server": server,
            "port": int(''.join(filter(str.isdigit, port))),
            "udp": True
        }
    else:
        logger.warning("Invalid ss link format")
        return None

def resolve_ip(hostname):
    try:
        return socket.gethostbyname(hostname)
    except Exception as e:
        logger.warning(f"Could not resolve IP for {hostname}: {e}")
        return hostname

def build_clash_config(parsed_proxies):
    proxies = []
    proxy_names = []

    for p in parsed_proxies:
        ip = resolve_ip(p["server"])
        p["server"] = ip
        proxies.append(p)
        proxy_names.append(p["name"])

    clash_config = {
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "Auto",
                "type": "url-test",
                "proxies": proxy_names,
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300
            }
        ],
        "rules": [
            "MATCH,Auto"
        ]
    }
    return clash_config

def main():
    urls = [
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-1.csv",
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-2.csv",
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-3.csv",
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-4.csv"
    ]

    ss_links = []
    for i, url in enumerate(urls, 1):
        ss = fetch_config(url, i)
        if ss:
            ss_links.append(ss)

    parsed = [parse_ss_link(link) for link in ss_links if parse_ss_link(link)]
    clash_config = build_clash_config(parsed)

    with open("ProjectAinita_Clash.yaml", "w", encoding="utf-8") as f:
        yaml.dump(clash_config, f, allow_unicode=True, sort_keys=False)

    logger.info("✅ فایل کانفیگ کلش با موفقیت ساخته شد: ProjectAinita_Clash.yaml")

if __name__ == "__main__":
    main()
