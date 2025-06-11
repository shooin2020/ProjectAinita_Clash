import requests
import yaml
import socket
import logging
from urllib.parse import urlparse, parse_qs
import base64
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_URL = "https://raw.githubusercontent.com/4n0nymou3/ss-config-updater/refs/heads/main/configs.txt"

def fetch_config_txt(url):
    logging.info(f"Fetching config from: {url}")
    r = requests.get(url)
    r.raise_for_status()
    return r.text

def clean_ss_link(ss_link):
    # حذف کوئری استرینگ و فاصله‌ها
    ss_link = ss_link.strip()
    if '?' in ss_link:
        ss_link = ss_link.split('?')[0]
    return ss_link

def parse_ss_link(ss_link):
    """
    پارس کردن لینک ss://
    خروجی: دیکشنری شامل {server, port, cipher, password}
    """
    # حذف prefix ss://
    if not ss_link.startswith("ss://"):
        raise ValueError("Not a valid ss link")

    content = ss_link[5:]  # بعد از ss://

    # دو حالت:
    # 1- لینک به صورت base64 رمزنگاری شده است، که به شکل: ss://base64_string
    # 2- لینک به صورت مستقیم به شکل cipher:password@host:port

    # حالت base64 رو چک می‌کنیم
    if '@' not in content:
        # base64 decode
        try:
            # padding اگر نداشت اضافه کنیم
            padding = len(content) % 4
            if padding != 0:
                content += "=" * (4 - padding)
            decoded = base64.urlsafe_b64decode(content).decode()
            # decoded نمونه: chacha20-ietf-poly1305:password@host:port
            content = decoded
        except Exception as e:
            raise ValueError(f"Base64 decode error: {e}")

    # حالا content باید به شکل cipher:password@host:port باشد
    try:
        userinfo, serverinfo = content.split('@')
        cipher, password = userinfo.split(':', 1)
        host, port = serverinfo.split(':', 1)
    except Exception as e:
        raise ValueError(f"Parsing ss link failed: {e}")

    return {
        "server": host,
        "port": int(port),
        "cipher": cipher,
        "password": password,
    }

def resolve_ip(hostname):
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except Exception as e:
        logging.warning(f"Failed to resolve hostname {hostname}: {e}")
        return None

def build_clash_config(proxies):
    clash_proxies = []
    proxy_names = []

    for i, p in enumerate(proxies, start=1):
        name = f"Server-{i}"
        proxy_names.append(name)
        clash_proxies.append({
            "name": name,
            "type": "ss",
            "server": p["ip"],
            "port": p["port"],
            "cipher": p["cipher"],
            "password": p["password"],
            "udp": True
        })

    config = {
        "proxies": clash_proxies,
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

    return config

def main():
    text = fetch_config_txt(CONFIG_URL)
    ss_links = []

    # هر خط حاوی ss:// استخراج شود
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("ss://"):
            cleaned = clean_ss_link(line)
            ss_links.append(cleaned)

    logging.info(f"Found {len(ss_links)} ss links")

    proxies = []
    for ss_link in ss_links:
        try:
            parsed = parse_ss_link(ss_link)
            ip = resolve_ip(parsed["server"])
            if ip:
                parsed["ip"] = ip
                proxies.append(parsed)
            else:
                logging.warning(f"Could not resolve IP for {parsed['server']}")
        except Exception as e:
            logging.error(f"Failed to parse {ss_link}: {e}")

    if not proxies:
        logging.error("No valid proxies found!")
        return

    # فقط ۴ تا اول
    proxies = proxies[:4]

    config = build_clash_config(proxies)

    with open("ProjectAinita_Clash.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)

    logging.info("ProjectAinita_Clash.yaml generated successfully.")

if __name__ == "__main__":
    main()
