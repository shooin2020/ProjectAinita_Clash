import requests
import yaml
import socket

# لینک فایل config سرورها (می تونی اینجا تغییر بدی)
CONFIG_URL = "https://raw.githubusercontent.com/4n0nymou3/ss-config-updater/refs/heads/main/configs.txt"

def dns_lookup(hostname):
    try:
        return socket.gethostbyname(hostname)
    except Exception as e:
        print(f"خطا در DNS lookup برای {hostname}: {e}")
        return hostname  # اگر نشد، همون hostname رو برگردون

def parse_ss_url(ss_url):
    # ss://{method}:{password}@{hostname}:{port}#{name}
    # یا ممکنه ss:// base64encoded...
    # برای ساده‌سازی اینجا فقط قسمت‌های معمول رو می‌گیریم
    if ss_url.startswith("ss://"):
        # حذف ss://
        content = ss_url[5:]
        # جدا کردن نام سرور (بعد از #)
        if '#' in content:
            content, name = content.split('#', 1)
        else:
            name = "Unnamed"
        # اگر base64 باشه ساده نیست، فرض می‌کنیم این شکل است:
        # method:password@hostname:port
        try:
            creds, host_port = content.split('@')
            method, password = creds.split(':')
            hostname, port = host_port.split(':')
            port = int(port)
        except Exception as e:
            print(f"خطا در پارس کردن لینک {ss_url}: {e}")
            return None
        return {
            "name": name,
            "method": method,
            "password": password,
            "hostname": hostname,
            "port": port
        }
    else:
        print(f"فرمت لینک اشتباه است: {ss_url}")
        return None

def build_clash_yaml(proxies):
    proxy_list = []
    for p in proxies:
        proxy_list.append({
            'name': p['name'],
            'type': 'ss',
            'server': p['ip'],   # ip از DNS lookup
            'port': p['port'],
            'cipher': p['method'],
            'password': p['password'],
            'udp': True
        })

    yaml_dict = {
        'proxies': proxy_list,
        'proxy-groups': [{
            'name': 'ProjectAinita',
            'type': 'select',
            'proxies': [p['name'] for p in proxies]
        }],
        'rules': [
            'MATCH,ProjectAinita'
        ]
    }

    return yaml.dump(yaml_dict, sort_keys=False, allow_unicode=True)

def main():
    print("در حال دریافت فایل config...")
    r = requests.get(CONFIG_URL)
    if r.status_code != 200:
        print("خطا در دریافت فایل config")
        return

    lines = r.text.strip().splitlines()
    proxies = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parsed = parse_ss_url(line)
        if parsed is None:
            continue
        # DNS lookup برای hostname
        ip = dns_lookup(parsed['hostname'])
        parsed['ip'] = ip
        proxies.append(parsed)

    if not proxies:
        print("هیچ پروکسی معتبری پیدا نشد")
        return

    print(f"تعداد پروکسی‌های معتبر: {len(proxies)}")

    # ساخت فایل YAML
    yaml_content = build_clash_yaml(proxies)

    # ذخیره در فایل
    filename = "ProjectAinita_Clash.yaml"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    print(f"فایل کلش ساخته شد: {filename}")

if __name__ == "__main__":
    main()
