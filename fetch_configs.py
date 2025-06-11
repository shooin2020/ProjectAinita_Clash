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
        decoded_creds = base64.b64decode(creds + '==').decode('utf-8')  # Add padding if needed
        cipher, password = decoded_creds.split(':')
        # Split server and port
        server, port = server_info.split(':')
        port = port.split('/')[0]  # Remove any query params
        logger.info(f"Parsed SS URL: cipher={cipher}, password={password}, server={server}, port={port}")
        return cipher, password, server, int(port)
    except Exception as e:
        logger.error(f"Error parsing SS URL {ss_url}: {str(e)}")
        return None

def resolve_ips(hostname):
    """Resolve hostname to a list of IP addresses."""
    try:
        # Get all IP addresses for the hostname
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET)
        # Extract unique IPs
        ips = list(set(info[4][0] for info in addr_info))
        logger.info(f"Resolved {hostname} to IPs: {ips}")
        return ips
    except socket.gaierror as e:
        logger.warning(f"Failed to resolve {hostname}: {str(e)}. Falling back to hostname.")
        return [hostname]
    except Exception as e:
        logger.error(f"Unexpected error resolving {hostname}: {str(e)}")
        return [hostname]

def fetch_config(url, server_number, ip_list, used_ips):
    """Fetch config and assign a unique IP from ip_list."""
    https_url = url.replace('ssconf://', 'https://')
    logger.info(f"Fetching config from: {https_url}")
    
    try:
        response = requests.get(https_url, timeout=10)
        response.raise_for_status()
        content = response.text.strip()
        logger.info(f"Raw content from {https_url}: {content}")
        if content.startswith('ss://'):
            content = f"{content}#Server-{server_number}"
            logger.info(f"Successfully fetched config from {https_url}")
            # Extract details
            details = extract_ss_details(content)
            if details:
                cipher, password, hostname, port = details
                # Select an unused IP from ip_list
                for ip in ip_list:
                    if ip not in used_ips:
                        used_ips.add(ip)
                        logger.info(f"Assigned IP {ip} to Server-{server_number}")
                        return {
                            'name': f"Server-{server_number}",
                            'type': 'ss',
                            'server': ip,
                            'port': port,
                            'cipher': cipher,
                            'password': password
                        }
                # If no unused IPs, fall back to hostname
                logger.warning(f"No unused IPs available for Server-{server_number}. Using hostname {hostname}.")
                return {
                    'name': f"Server-{server_number}",
                    'type': 'ss',
                    'server': hostname,
                    'port': port,
                    'cipher': cipher,
                    'password': password
                }
            logger.error(f"Invalid config format or IP assignment failed for {https_url}")
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

    # Resolve IPs for the hostname (assuming all servers use the same hostname)
    sample_url = urls[0]
    sample_content = requests.get(sample_url.replace('ssconf://', 'https://'), timeout=10).text.strip()
    if sample_content.startswith('ss://'):
        _, _, hostname, _ = extract_ss_details(sample_content)
        ip_list = resolve_ips(hostname)
    else:
        logger.error("Could not determine hostname from first URL")
        ip_list = []

    proxies = []
    used_ips = set()  # Track used IPs to ensure uniqueness
    for index, url in enumerate(urls, 1):
        logger.info(f"Processing URL: {url}")
        config = fetch_config(url, index, ip_list, used_ips)
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
