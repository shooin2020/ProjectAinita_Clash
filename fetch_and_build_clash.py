import requests
import logging
import base64
import socket
import yaml

logging.basicConfig(level=logging.INFO)

HEADERS = """//profile-title: base64:YWluaXRhLm5ldA==
//profile-update-interval: 1
//subscription-userinfo: upload=0; download=0; total=10737418240000000; expire=2546249531
//support-url: info@ainita.net
//profile-web-page-url: https://ainita.net"""

URLS = [
    "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-1.csv",
    "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-2.csv",
    "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-3.csv",
    "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-4.csv"
]

def fetch_config(url, server_number):
    https_url = url.replace('ssconf://', 'https://')
    logging.info(f"Fetching config from: {https_url}")
    try:
        response = requests.get(https_url, timeout=10)
        response.raise_for_status()
        content = response.text.strip()
        if content.startswith('ss://'):
            content = f"{content}#Server-{server_number}"
            logging.info(f"Fetched config for server {server_number}")
            return content
        else:
            logging.error(f"Invalid config format from {https_url}")
            return None
    except Exception as e:
        logging.error(f"Error fetching {https_url}: {e}")
        return None

def resolve_domain_to_ips(domain, max_ips=4):
    try:
        # فقط IPv4
        ips = socket.gethostbyname_ex(domain)[2]
        return ips[:max_ips]
    except Exception as e:
        logging.error(f"DNS lookup failed for {domain}: {e}")
        return []

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
            decoded = base64.urlsafe_b64decode(userinfo + '===').decode()
        except Exception:
            decoded = userinfo

        if ':' in decoded:
            cipher, password = decoded.split(':', 1)
        else:
            cipher = decoded
            password = ""

        if ':' in hostport:
            server, port = hostport.split(':', 1)
            port = int(port)
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
        logging.warning("Complex ss link format not handled")
        return None

def main():
    configs = []
    for i, url in enumerate(URLS, 1):
        config = fetch_config(url, i)
        if config:
            configs.append(config)

    if not configs:
        logging.error("No configs fetched!")
        exit(1)

    proxies = []
    proxy_names = []

    for ss_link in configs:
        base_proxy = parse_ss_link(ss_link)
        if base_proxy:
            # آی‌پی های دامنه را بگیریم
            ips = resolve_domain_to_ips(base_proxy['server'])
            if not ips:
                # اگر نشد، حداقل یکبار با همان دامنه ثبت کنیم
                proxies.append({
                    "name": base_proxy["base_name"] + "-IP0",
                    "type": "ss",
                    "server": base_proxy["server"],
                    "port": base_proxy["port"],
                    "cipher": base_proxy["cipher"],
                    "password": base_proxy["password"],
                    "udp": True
                })
                proxy_names.append(base_proxy["base_name"] + "-IP0")
            else:
                # برای هر IP یک پراکسی جدا بسازیم
                for idx, ip in enumerate(ips):
                    proxy_name = f"{base_proxy['base_name']}-IP{idx+1}"
                    proxies.append({
                        "name": proxy_name,
                        "type": "ss",
                        "server": ip,
                        "port": base_proxy["port"],
                        "cipher": base_proxy["cipher"],
                        "password": base_proxy["password"],
                        "udp": True
                    })
                    proxy_names.append(proxy_name)

    clash_dict = {
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "ProjectAinita",
                "type": "select",
                "proxies": proxy_names
            }
        ],
        "rules": [
            "MATCH,ProjectAinita"
        ]
    }

    with open('ProjectAinita_Clash.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(clash_dict, f, allow_unicode=True, sort_keys=False)

    logging.info("Clash config file created: ProjectAinita_Clash.yaml")

if __name__ == "__main__":
    main()
