import requests
import logging
import socket
import base64
import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_ss_details(ss_url):
    """Extract cipher, password, server, and port from ss:// URL."""
    try:
        # Remove 'ss://' and split at '#'
        ss_part = ss_url.split('#')[0].replace('ss://', '')
        # Split at '@' to separate credentials and server info
        creds, server_info = ss_part.split('@')
        # Decode base64 credentials (cipher:password)
        decoded_creds = base64.b64decode(creds).decode('utf-8')
        cipher, password = decoded_creds.split(':')
        # Split server and port
        server, port = server_info.split(':')
        port = port.split('/')[0]  # Remove any query params
        return cipher, password, server, int(port)
    except Exception as e:
        logger.error(f"Error parsing SS URL: {str(e)}")
        return None

def resolve_ip(hostname):
    """Resolve hostname to IP address."""
    try:
        ip = socket.gethostbyname(hostname)
        logger.info(f"Resolved {hostname} to {ip}")
        return ip
    except socket.gaierror as e:
        logger.error(f"Error resolving {hostname}: {str(e)}")
        return None

def fetch_config(url, server_number):
    https_url = url.replace('ssconf://', 'https://')
    logger.info(f"Fetching config from: {https_url}")
    
    try:
        response = requests.get(https_url, timeout=10)
        response.raise_for_status()
        content = response.text.strip()
        if content.startswith('ss://'):
            content = f"{content}#Server-{server_number}"
            logger.info(f"Successfully fetched config from {https_url}")
            # Extract details
            details = extract_ss_details(content)
            if details:
                cipher, password, hostname, port = details
                # Resolve IP
                ip = resolve_ip(hostname)
                if ip:
                    return {
                        'name': f"Server-{server_number}",
                        'type': 'ss',
                        'server': ip,
                        'port': port,
                        'cipher': cipher,
                        'password': password
                    }
            logger.error(f"Invalid config format or IP resolution failed for {https_url}")
            return None
        else:
            logger.error(f"Invalid config format from {https_url}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {https_url}: {str(e)}")
        return None

def main():
    logger.info("Starting config fetch process")

    urls = [
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-1.csv",
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-2.csv",
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-3.csv",
        "ssconf://ainita.s3.eu-north-1.amazonaws.com/AinitaServer-4.csv"
    ]

    proxies = []
    for index, url in enumerate(urls, 1):
        logger.info(f"Processing URL: {url}")
        config = fetch_config(url, index)
        if config:
            proxies.append(config)
    
    if not proxies:
        logger.error("No configs were successfully fetched!")
        exit(1)

    try:
        config_yaml = {'proxies': proxies}
        with open('configs.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config_yaml, f, allow_unicode=True, sort_keys=False)
        logger.info(f"Successfully wrote {len(proxies)} configs to configs.yaml")
    except Exception as e:
        logger.error(f"Error writing to file: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
