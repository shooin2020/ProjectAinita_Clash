import requests
import base64
import socket
import yaml

CONFIGS_URL = "https://raw.githubusercontent.com/4n0nymou3/ss-config-updater/refs/heads/main/configs.txt"
OUTPUT_FILE = "ProjectAinita_Clash.yaml"

def resolve_ip(domain):
    try:
        return socket.gethostbyname(domain)
    except Exception as e:
        print(f"⚠️ خطا در DNS Lookup برای {domain}: {e}")
        return domain  # اگر نشد، خود دامنه را برمی‌گردانیم

def parse_ss_url(ss_url):
    """
    پارس کردن لینک ss://  
    ساختار: ss://base64(method:password)@domain:port#tag
    """
    try:
        prefix_removed = ss_url[5:]  # حذف "ss://"
        userinfo, rest = prefix_removed.split("@", 1)
        server_port_tag = rest.split("#")
        server_port = server_port_tag[0]
        tag = server_port_tag[1] if len(server_port_tag) > 1 else "Unnamed"

        method_password = base64.urlsafe_b64decode(userinfo + "==").decode()
        method, password = method_password.split(":", 1)

        server = server_port.split(":")[0]
        port = int(server_port.split(":")[1])

        return {
            "name": tag,
            "server": server,
            "port": port,
            "password": password,
            "method": method,
        }
    except Exception as e:
        print(f"❌ خطا در پارس کردن لینک {ss_url}: {e}")
        return None

def main():
    r = requests.get(CONFIGS_URL)
    if r.status_code != 200:
        print("⛔ خطا در دریافت فایل configs.txt")
        return

    lines = r.text.strip().splitlines()
    servers = []
    for line in lines:
        if not line.startswith("ss://"):
            continue
        parsed = parse_ss_url(line)
        if parsed is None:
            continue

        # پیدا کردن IP واقعی
        ip = resolve_ip(parsed["server"])
        parsed["ip"] = ip
        servers.append(parsed)

        if len(servers) >= 4:  # فقط 4 سرور لازم داریم
            break

    if not servers:
        print("❌ هیچ سروری پیدا نشد")
        return

    # ساختار فایل کلش
    clash_yaml = {
        "proxies": [],
        "proxy-groups": [
            {
                "name": "ProjectAinita",
                "type": "select",
                "proxies": []
            }
        ],
        "rules": [
            "MATCH,ProjectAinita"
        ]
    }

    for srv in servers:
        proxy = {
            "name": srv["name"],
            "type": "ss",
            "server": srv["ip"],
            "port": srv["port"],
            "cipher": srv["method"],
            "password": srv["password"],
        }
        clash_yaml["proxies"].append(proxy)
        clash_yaml["proxy-groups"][0]["proxies"].append(srv["name"])

    # ذخیره فایل
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        yaml.dump(clash_yaml, f, allow_unicode=True)

    print(f"✅ فایل {OUTPUT_FILE} با موفقیت ساخته شد.")

if __name__ == "__main__":
    main()
