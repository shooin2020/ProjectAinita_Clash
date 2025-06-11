import requests
import base64
import logging
import socket

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fetch_config(url, server_number):
    https_url = url.replace('ssconf://', 'https://')
    logger.info(f"Fetching config from: {https_url}")
    try:
        response = requests.get(https_url, timeout=10)
        response.raise_for_status()
        content = response.text.strip()
        if content.startswith('ss://'):
            content = f"{content}#Server-{server_number}"
            logger.info(f"Fetched config for server {server_number}")
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
            server, port_and_params = hostport.split(':', 1)
            port_str = ''
            for ch in port_and_params:
                if ch.isdigit():
                    port_str += ch
                else:
                    break
            port = int(port_str) if port_str else 0
        else:
            server = hostport
            port = 0

        return {
            "tag": tag,
            "cipher": cipher,
            "password": password,
            "server": server,
            "port": port
        }
    else:
        logger.warning("Invalid ss link format")
        return None

def resolve_first_ip(hostname):
    try:
        ip = socket.gethostbyname(hostname)
        logger.info(f"Resolved IP for {hostname}: {ip}")
        return ip
    except Exception as e:
        logger.error(f"DNS resolution failed for {hostname}: {str(e)}")
        return hostname

def build_clash_yaml(ss_links):
    proxies = []
    proxy_names = []

    for i, ss_link in enumerate(ss_links, 1):
        parsed = parse_ss_link(ss_link)
        if not parsed:
            continue

        ip = resolve_first_ip(parsed["server"])
        tag = f"Server-{i}"
        proxy_str = (
            f"ss://{base64.urlsafe_b64encode(f'{parsed['cipher']}:{parsed['password']}'.encode()).decode().rstrip('=')}"
            f"@{ip}:{parsed['port']}#{tag}"
        )
        proxies.append(proxy_str)
        proxy_names.append(tag)

    yaml_lines = []
    yaml_lines.append("proxies: &id001")
    for p in proxies:
        yaml_lines.append(f"- {p}")
    yaml_lines.append("proxy-groups:")
    yaml_lines.append("- name: ProjectAinita")
    yaml_lines.append("  proxies: *id001")
    yaml_lines.append("  type: select")
    yaml_lines.append("rules:")
    yaml_lines.append("- MATCH,ProjectAinita")

    return "\n".join(yaml_lines)

def main():
    urls = [
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-1.csv",
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-2.csv",
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-3.csv",
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-4.csv"
    ]

    configs = []
    for i, url in enumerate(urls, 1):
        config = fetch_config(url, i)
        if config:
            configs.append(config)

    if not configs:
        logger.error("No configs fetched")
        return

    yaml = build_clash_yaml(configs)

    try:
        with open("ProjectAinita_Clash.yaml", "w", encoding="utf-8") as f:
            f.write(yaml)
        logger.info("Clash config written to ProjectAinita_Clash.yaml")
    except Exception as e:
        logger.error(f"Error writing YAML: {e}")

if __name__ == "__main__":
    main()
