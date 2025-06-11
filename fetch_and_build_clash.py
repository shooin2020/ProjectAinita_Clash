import base64
import requests
import logging
import re
import socket
import yaml

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HEADERS = """//profile-title: base64:YWluaXRhLm5ldA==
//profile-update-interval: 1
//subscription-userinfo: upload=0; download=0; total=10737418240000000; expire=2546249531
//support-url: info@ainita.net
//profile-web-page-url: https://ainita.net"""

# لینک‌های سرورهای Ainita
URLS = [
    "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-1.csv",
    "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-2.csv",
    "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-3.csv",
    "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-4.csv"
]

def base64_decode_ss_link(ss_link):
    """بخش Base64 لینک ss:// را decode می‌کند"""
    # ss_link بدون ss://
    if ss_link.startswith("ss://"):
        ss_link = ss_link[5:]
    # حذف احتمالی پسوند (بعد از #)
    ss_link = ss_link.split('#')[0]
    # decode با padding مناسب base64
    missing_padding = len(ss_link) % 4
    if missing_padding:
        ss_link += '=' * (4 - missing_padding)
    try:
        decoded = base64.urlsafe_b64decode(ss_link).decode('utf-8')
        return decoded
    except Exception as e:
        logger.error(f"Base64 decode error for {ss_link}: {e}")
        return None

def parse_ss_link(ss_link):
    """
    لینک ss:// دیکد شده را به دیکشنری شامل
    cipher, password, server, port تبدیل می‌کند
    """
    decoded = base64_decode_ss_link(ss_link)
    if not decoded:
        raise ValueError("Invalid Base64 or empty decoded string")

    # regex برای گرفتن cipher, password, host, port
    # ساختار نمونه: chacha20-ietf-poly1305:password@hostname:port
    pattern = r'^(?P<cipher>[^:]+):(?P<password>[^@]+)@(?P<host>[^:]+):(?P<port>\d+)'
    match = re.match(pattern, decoded)
    if not match:
        raise ValueError(f"Invalid SS link format: {decoded}")

    return {
        "cipher": match.group("cipher"),
        "password": match.group("password"),
        "server": match.group("host"),
        "port": int(match.group("port"))
    }

def resolve_ip(hostname):
    """نام دامنه را به IP حل می‌کند"""
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except Exception as e:
        logger.error(f"DNS resolution failed for {hostname}: {e}")
        return None

def fetch_config(url, server_number):
    https_url = url.replace('ssconf://', 'https://')
    logger.info(f"Fetching config from: {https_url}")

    try:
        response = requests.get(https_url, timeout=10)
        response.raise_for_status()
        content = response.text.strip()

        if content.startswith('ss://'):
            # لینک ss:// خالص
            ss_link = content
        else:
            logger.error(f"Invalid config format from {https_url}: does not start with ss://")
            return None

        return ss_link + f"#Server-{server_number}"
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {https_url}: {e}")
        return None

def build_clash_config(ss_links):
    """ساخت دیکشنری YAML برای کلش"""
    proxies = []
    proxy_names = []

    for i, ss_link in enumerate(ss_links, 1):
        try:
            ss_info = parse_ss_link(ss_link)
            ip = resolve_ip(ss_info['server'])
            if not ip:
                logger.warning(f"Skipping server {ss_info['server']} due to DNS failure")
                continue

            proxy = {
                'name': f"Server-{i}",
                'type': 'ss',
                'server': ip,
                'port': ss_info['port'],
                'cipher': ss_info['cipher'],
                'password': ss_info['password'],
                'udp': True
            }
            proxies.append(proxy)
            proxy_names.append(proxy['name'])
        except Exception as e:
            logger.error(f"Error parsing or building proxy from link: {ss_link}, error: {e}")

    # ساخت proxy-group با همه سرورها
    proxy_group = {
        'name': 'Auto',
        'type': 'url-test',
        'proxies': proxy_names,
        'url': 'http://www.gstatic.com/generate_204',
        'interval': 300
    }

    clash_config = {
        'proxies': proxies,
        'proxy-groups': [proxy_group],
        'rules': ['MATCH,Auto']
    }

    return clash_config

def main():
    logger.info("Starting config fetch process")
    ss_links = []

    for idx, url in enumerate(URLS, 1):
        ss_link = fetch_config(url, idx)
        if ss_link:
            logger.info(f"Fetched config for server {idx}")
            ss_links.append(ss_link)

    if not ss_links:
        logger.error("No valid ss:// configs fetched, exiting.")
        exit(1)

    clash_config = build_clash_config(ss_links)

    # ذخیره فایل YAML
    output_file = 'ProjectAinita_Clash.yaml'
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(clash_config, f, allow_unicode=True)
        logger.info(f"Successfully wrote Clash config to {output_file}")
    except Exception as e:
        logger.error(f"Failed to write Clash config file: {e}")
        exit(1)

if __name__ == "__main__":
    main()
