import requests
import yaml
import logging
import re

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

def save_configs_to_file(configs, filename='configs.txt'):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(HEADERS + '\n\n')
        f.write('\n\n'.join(configs))
    logging.info(f"Wrote {len(configs)} configs to {filename}")

def parse_configs_file(filename='configs.txt'):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # استخراج خطوط ss://
    ss_lines = re.findall(r'(ss://[^\s#]+(?:#[^\s]+)?)', content)
    proxies = []
    for line in ss_lines:
        # می‌تونید اینجا تبدیل‌های لازم به دیکشنری proxy انجام بدید
        proxies.append(line.strip())
    logging.info(f"Parsed {len(proxies)} proxies from {filename}")
    return proxies

def build_clash_yaml(proxies, filename='ProjectAinita_Clash.yaml'):
    clash_dict = {
        'proxies': proxies,
        'proxy-groups': [
            {
                'name': 'ProjectAinita',
                'type': 'select',
                'proxies': proxies
            }
        ],
        'rules': [
            'MATCH,ProjectAinita'
        ]
    }

    # اگر لازم بود تبدیل proxies به ساختار دقیق‌تر Clash انجام بدید، اینجا باید ویرایش کنید
    # الان فقط ss:// لینک‌ها داخل proxies هستند که ممکنه clash قبول نکنه و نیاز به parse دقیق‌تر هست

    with open(filename, 'w', encoding='utf-8') as f:
        yaml.dump(clash_dict, f, allow_unicode=True)
    logging.info(f"Created Clash config file: {filename}")

def main():
    configs = []
    for i, url in enumerate(URLS, 1):
        config = fetch_config(url, i)
        if config:
            configs.append(config)
    if not configs:
        logging.error("No configs fetched!")
        exit(1)

    save_configs_to_file(configs)

    proxies = parse_configs_file()
    build_clash_yaml(proxies)

if __name__ == "__main__":
    main()
