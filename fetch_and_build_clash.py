import base64
import requests
import socket
import yaml
from urllib.parse import urlparse, unquote

AINTIA_CSV_LINKS = [
    "https://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-1.csv",
    "https://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-2.csv",
    "https://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-3.csv",
    "https://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-4.csv",
]

def resolve_domain_to_ips(domain):
    try:
        return list(set(item[4][0] for item in socket.getaddrinfo(domain, None)))
    except:
        return []

def parse_ss_url(ss_url):
    if ss_url.startswith("ss://"):
        ss_url = ss_url[5:]
    if '#' in ss_url:
        ss_url, tag = ss_url.split('#', 1)
    else:
        tag = 'Ainita'
    if '@' in ss_url:
        creds_enc, server_info = ss_url.split('@')
        creds = base64.urlsafe_b64decode(creds_enc + '=' * (-len(creds_enc) % 4)).decode()
    else:
        decoded = base64.urlsafe_b64decode(ss_url + '=' * (-len(ss_url) % 4)).decode()
        creds, server_info = decoded.split('@')
    method, password = creds.split(':')
    server, port = server_info.split(':')
    return method, password, server, port, tag

def build_clash_proxies(ss_links):
    proxies = []
    used_ips = []
    for i, ss in enumerate(ss_links):
        try:
            method, password, domain, port, tag = parse_ss_url(ss)
            ips = resolve_domain_to_ips(domain)
            if not ips:
                continue
            ip = [ip for ip in ips if ip not in used_ips]
            ip = ip[0] if ip else ips[0]
            used_ips.append(ip)
            proxies.append({
                "name": f"{tag}",
                "type": "ss",
                "server": ip,
                "port": int(port),
                "cipher": method,
                "password": password,
                "udp": True
            })
        except Exception as e:
            print(f"خطا در پردازش لینک: {ss} → {e}")
    return proxies

def fetch_ss_links():
    links = []
    for i, url in enumerate(AINTIA_CSV_LINKS, start=1):
        try:
            res = requests.get(url)
            if res.status_code == 200:
                content = res.text.strip().splitlines()
                for line in content:
                    if line.startswith("ss://"):
                        links.append(f"{line}#Server-{i}")
        except Exception as e:
            print(f"خطا در دریافت {url}: {e}")
    return links

def build_clash_config(proxies):
    config = {
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "ProjectAinita",
                "type": "select",
                "proxies": [p["name"] for p in proxies]
            }
        ],
        "rules": ["MATCH,ProjectAinita"]
    }
    with open("ProjectAinita_Clash.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True)

if __name__ == "__main__":
    print("⏬ در حال دریافت لینک‌ها از Ainita...")
    ss_links = fetch_ss_links()
    print("✅ لینک‌ها دریافت شد.")
    proxies = build_clash_proxies(ss_links)
    build_clash_config(proxies)
    print("✅ فایل نهایی ProjectAinita_Clash.yaml ساخته شد.")
