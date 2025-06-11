import requests
import base64
import logging
import socket

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

HEADERS = """//profile-title: base64:YWluaXRhLm5ldA==
//profile-update-interval: 1
//subscription-userinfo: upload=0; download=0; total=10737418240000000; expire=2546249531
//support-url: info@ainita.net
//profile-web-page-url: https://ainita.net"""

def fetch_config(url, server_number):
    https_url = url.replace('ssconf://', 'https://')
    logger.info(f"Fetching config from: {https_url}")
    
    try:
        response = requests.get(https_url, timeout=10)
        response.raise_for_status()
        content = response.text.strip()
        if content.startswith('ss://'):
            content = f"{content}#Server-{server_number}"
            logger.info(f"Successfully fetched config from {https_url} and added server number")
            return content
        else:
            logger.error(f"Invalid config format from {https_url}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {https_url}: {str(e)}")
        return None

def parse_ss_link(ss_link):
    """
    پارس کردن لینک ss:// و تبدیل به دیکشنری اولیه
    """
    parts = ss_link.split('#')
    tag = parts[1] if len(parts) > 1 else "Unnamed"

    link_body = parts[0][5:]

    if '@' in link_body:
        userinfo, hostport = link_body.split('@', 1)
        try:
            # padding اضافه برای base64
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
            # استخراج عدد پورت تا جایی که عدد است
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
            "base_name": tag,
            "cipher": cipher,
            "password": password,
            "server": server,
            "port": port,
            "udp": True
        }
    else:
        logger.warning("Complex ss link format not handled")
        return None

def resolve_ip(server):
    try:
        ip_list = socket.gethostbyname_ex(server)[2]
        logger.info(f"Resolved IPs for {server}: {ip_list}")
        return ip_list[:4]  # حداکثر ۴ آی پی
    except Exception as e:
        logger.error(f"DNS resolution failed for {server}: {str(e)}")
        return []

def build_clash_yaml(ss_links):
    proxies = []
    proxy_names = []

    for i, ss_link in enumerate(ss_links, 1):
        base_proxy = parse_ss_link(ss_link)
        if not base_proxy:
            logger.error(f"Failed to parse ss link: {ss_link}")
            continue

        ips = resolve_ip(base_proxy["server"])
        if not ips:
            logger.warning(f"No IPs found for server {base_proxy['server']}, using hostname")
            ips = [base_proxy["server"]]

        for ip_index, ip in enumerate(ips, 1):
            proxy_name = f"Server-{i}-{ip_index}"
            proxy_str = (
                f"ss://{base64.urlsafe_b64encode(f'{base_proxy['cipher']}:{base_proxy['password']}'.encode()).decode().rstrip('=')}@{ip}:{base_proxy['port']}#"
                + proxy_name
            )
            proxies.append(proxy_str)
            proxy_names.append(proxy_name)

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
    logger.info("Starting config fetch process")

    urls = [
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-1.csv",
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-2.csv",
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-3.csv",
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-4.csv"
    ]

    configs = []
    for index, url in enumerate(urls, 1):
        config = fetch_config(url, index)
        if config:
            configs.append(config)
    
    if not configs:
        logger.error("No configs were successfully fetched!")
        exit(1)

    clash_yaml = build_clash_yaml(configs)

    try:
        with open('ProjectAinita_Clash.yaml', 'w', encoding='utf-8') as f:
            f.write(clash_yaml)
        logger.info("Successfully wrote Clash config to ProjectAinita_Clash.yaml")
    except Exception as e:
        logger.error(f"Error writing to file: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
