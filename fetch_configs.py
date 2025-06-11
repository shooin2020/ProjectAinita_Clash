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
    """Resolve hostname to a list of unique IP addresses."""
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

def fetch_config(url, server_number):
    """Fetch config and extract details."""
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
                return {
                    'name': f"Server-{server_number}",
                    'cipher': cipher,
                    'password': password,
                    'hostname': hostname,
                    'port': port
                }
            logger.error(f"Invalid config format for {https_url}")
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

    # Fetch configs and collect hostname details
    configs = []
    for index, url in enumerate(urls, 1):
        logger.info(f"Processing URL: {url}")
        config = fetch_config(url, index)
        if config:
            configs.append(config)
    
    if not configs:
        logger.error("No configs were successfully fetched!")
        exit(1)

    # Collect unique hostnames and resolve IPs
    hostnames = set(config['hostname'] for config in configs)
    logger.info(f"Unique hostnames found: {hostnames}")
    
    ip_to_config = {}
    for hostname in hostnames:
        ips = resolve_ips(hostname)
        for ip in ips:
            # Find the first config with this hostname to get cipher, password, port
            for config in configs:
                if config['hostname'] == hostname:
                    ip_to_config[ip] = {
                        'cipher': config['cipher'],
                        'password': config['password'],
                        'port': config['port']
                    }
                    break

    # Create proxies for each unique IP
    proxies = []
    for index, (ip, config_details) in enumerate(ip_to_config.items(), 1):
        proxies.append({
            'name': f"Server-{index}",
            'type': 'ss',
            'server': ip,
            'port': config_details['port'],
            'cipher': config_details['cipher'],
            'password': config_details['password']
        })

    if not proxies:
        logger.error("No IPs were resolved, falling back to hostnames!")
        # Fallback to hostnames if no IPs are resolved
        for index, config in enumerate(configs, 1):
            proxies.append({
                'name': f"Server-{index}",
                'type': 'ss',
                'server': config['hostname'],
                'port': config['port'],
                'cipher': config['cipher'],
                'password': config['password']
            })

    try:
        config_yaml = {'proxies': proxies}
        with open('ProjectAinita_Clash.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config_yaml, f, allow_unicode=True, sort_keys=False)
        logger.info(f"Successfully wrote {len(proxies)} configs to ProjectAinita_Clash.yaml")
    except Exception as e:
        logger.error(f"Error writing to file: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
