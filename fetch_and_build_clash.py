import logging
import requests
import base64
from urllib.parse import urlparse, unquote
import yaml

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERVER_URLS = [
    "https://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-1.csv",
    "https://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-2.csv",
    "https://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-3.csv",
    "https://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-4.csv",
]

def fetch_csv(url):
    logger.info(f"Fetching config from: {url}")
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.text

def extract_ss_links(csv_text):
    # هر خطی که با ss:// شروع شود را جدا می‌کنیم
    ss_links = []
    for line in csv_text.splitlines():
        line = line.strip()
        if line.startswith("ss://"):
            ss_links.append(line)
    return ss_links

def parse_ss_link(ss_link):
    try:
        if not ss_link.startswith("ss://"):
            logger.error("Not a valid ss:// link")
            return None

        ss_body = ss_link[5:]

        # اگر @ در ss_body نبود، احتمالا base64 encoded است (روش قدیمی)
        if '@' not in ss_body:
            base64_part = ss_body.split('#')[0]
            missing_padding = len(base64_part) % 4
            if missing_padding:
                base64_part += '=' * (4 - missing_padding)
            decoded = base64.urlsafe_b64decode(base64_part).decode('utf-8')
            ss_body = decoded
            # اضافه کردن remark اگر بود
            if '#' in ss_link:
                remark = ss_link.split('#', 1)[1]
                ss_body += '#' + remark

        remark = None
        if '#' in ss_body:
            ss_body, remark = ss_body.split('#', 1)

        userinfo, hostinfo = ss_body.split('@', 1)
        cipher, password = userinfo.split(':', 1)

        # استفاده از urlparse برای حذف query string اضافی و گرفتن سرور و پورت
        parsed = urlparse('//' + hostinfo)
        server = parsed.hostname
        port = parsed.port
        if port is None:
            logger.error(f"Port missing in ss link: {ss_link}")
            return None

        password = unquote(password)

        return {
            "name": remark if remark else "Unnamed",
            "server": server,
            "port": port,
            "cipher": cipher,
            "password": password,
            "udp": True
        }
    except Exception as e:
        logger.error(f"Error parsing ss link {ss_link}: {str(e)}")
        return None

def build_clash_config(proxies):
    proxy_entries = []
    proxy_names = []

    for idx, proxy in enumerate(proxies, start=1):
        proxy_name = f"Server-{idx}"
        proxy_names.append(proxy_name)
        proxy_entries.append({
            "name": proxy_name,
            "type": "ss",
            "server": proxy["server"],
            "port": proxy["port"],
            "cipher": proxy["cipher"],
            "password": proxy["password"],
            "udp": True
        })

    config = {
        "proxies": proxy_entries,
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
    all_proxies = []

    for url in SERVER_URLS:
        try:
            csv_text = fetch_csv(url)
            ss_links = extract_ss_links(csv_text)
            if not ss_links:
                logger.warning(f"No ss links found in {url}")
                continue

            # فقط اولین ss لینک هر فایل را می‌گیریم (اگر چند تا بود)
            ss_link = ss_links[0]
            proxy = parse_ss_link(ss_link)
            if proxy:
                all_proxies.append(proxy)
            else:
                logger.warning(f"Could not parse proxy from {url}")
        except Exception as e:
            logger.error(f"Failed to process {url}: {e}")

    if len(all_proxies) < 4:
        logger.error(f"Only found {len(all_proxies)} valid proxies, need 4 to proceed. Exiting.")
        return

    # فقط ۴ تا سرور اول رو استفاده کن
    final_proxies = all_proxies[:4]

    config = build_clash_config(final_proxies)

    with open("output.yaml", "w") as f:
        yaml.dump(config, f, sort_keys=False, allow_unicode=True)

    logger.info("Clash config file 'output.yaml' generated successfully.")

if __name__ == "__main__":
    main()
