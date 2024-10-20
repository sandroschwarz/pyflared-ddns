#!/usr/bin/env python3
import os
import requests
import argparse
import logging
from datetime import datetime
from dotenv import load_dotenv
from cloudflare import Cloudflare

# Load environment variables from .env file
load_dotenv()


# Function to set up logging
def setup_logging():
    """Set up the logging configuration to write logs to a subfolder 'logs'."""
    log_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "logs")

    # Create the 'logs' folder if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Set the log file name with a timestamp
    log_file = os.path.join(log_dir, f"log_{datetime.now().strftime('%Y-%m-%d')}.log")

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),  # Also prints to console
        ],
    )

    logging.debug("Logging started")


# Initialize logging at the start
setup_logging()


def get_public_ip(version):
    """Get the public IPv4 or IPv6 address of the host."""
    if version == 4:
        ip_service = "https://v4.ident.me"
    elif version == 6:
        ip_service = "https://v6.ident.me"
    else:
        raise ValueError("IP version should be 4 or 6")

    try:
        response = requests.get(ip_service)
        response.raise_for_status()
        ip_address = response.text
        logging.debug(f"Fetched public IPv{version} address: {ip_address}")
        return ip_address
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching public IPv{version} address: {e}")
        return None


def get_cloudflare_client():
    """Initialize the Cloudflare client using the API token from .env."""
    api_token = os.getenv("CF_TOKEN")
    if not api_token:
        logging.error("Cloudflare API token (CF_TOKEN) not found in .env file.")
        raise ValueError("Cloudflare API token (CF_TOKEN) not found in .env file.")
    return Cloudflare(api_token=api_token)


def find_dns_record(cf, zone_id, record_type, hostname):
    """Find an existing DNS record by type and hostname."""
    try:
        dns_records = cf.dns.records.list(zone_id=zone_id)
        for record in dns_records:
            if record.type == record_type and record.name == hostname:
                return record
        return None
    except Exception as e:
        logging.error(f"Error fetching DNS records: {e}")
        return None


def create_dns_record(cf, zone_id, record_type, hostname, content):
    """Create a new DNS record."""
    try:
        cf.dns.records.create(
            # Create the specified record without having it be proxied.
            # "ttl=1" in this case means "automatic" here, for more info see the API documentation:
            # https://github.com/cloudflare/cloudflare-python/blob/main/src/cloudflare/types/dns/record_create_params.py
            zone_id=zone_id,
            content=content,
            name=hostname,
            type=record_type,
            ttl=1,
            proxied=False,
        )
        logging.info(
            f"Created a '{record_type}' record for {hostname} with content {content}"
        )
    except Exception as e:
        logging.error(f"Error creating DNS record: {e}")


def update_dns_record(cf, zone_id, hostname, content, record_type, dns_record_id):
    """Update an existing DNS record."""
    data = {"content": content}
    try:
        cf.dns.records.update(
            zone_id=zone_id,
            name=hostname,
            content=content,
            type=record_type,
            dns_record_id=dns_record_id,
        )
        logging.info(f"Updated DNS record {hostname} with content {content}")
    except Exception as e:
        logging.error(f"Error updating DNS record: {e}")


def sync_dns_record(cf, zone_id, record_type, hostname, public_ip):
    """Sync a DNS record (create or update)."""
    dns_record = find_dns_record(cf, zone_id, record_type, hostname)
    if dns_record:
        # If the record exists and the content (IP) differs, update it
        if dns_record.content != public_ip:
            logging.info(
                f"'{record_type}' record for {hostname} exists but IP differs. Updating..."
            )
            update_dns_record(
                cf,
                dns_record.zone_id,
                hostname,
                public_ip,
                dns_record.type,
                dns_record.id,
            )
        else:
            logging.info(
                f"'{record_type}' record for {hostname} is already up to date."
            )
    else:
        # If no record exists, create a new one
        logging.info(f"'{record_type}' record for {hostname} is missing. Creating...")
        create_dns_record(cf, zone_id, record_type, hostname, public_ip)


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Sync Cloudflare DNS records.")
    parser.add_argument(
        "--ipv4", action="store_true", help="Check and update A records (IPv4)."
    )
    parser.add_argument(
        "--ipv6", action="store_true", help="Check and update AAAA records (IPv6)."
    )
    parser.add_argument(
        "--both",
        action="store_true",
        help="Check and update both A and AAAA records (default behavior).",
    )

    args = parser.parse_args()

    # Initialize Cloudflare API client
    cf = get_cloudflare_client()

    # Get the zone id from the .env file
    hostname = os.getenv("CF_HOSTNAME")
    if not hostname:
        raise ValueError("Host name (CF_HOSTNAME) not found in .env file.")

    # Get the zone name from the .env file
    zone_id = os.getenv("CF_ZONE-ID")
    if not zone_id:
        raise ValueError("Zone name (CF_ZONE-ID) not found in .env file.")

    # Get the public IP addresses
    public_ipv4 = get_public_ip(4)
    public_ipv6 = get_public_ip(6)

    # Determine which records to sync
    if args.both or (not args.ipv4 and not args.ipv6):
        public_ipv4 = get_public_ip(4)
        public_ipv6 = get_public_ip(6)
        if public_ipv4:
            sync_dns_record(cf, zone_id, "A", hostname, public_ipv4)
        if public_ipv6:
            sync_dns_record(cf, zone_id, "AAAA", hostname, public_ipv6)

    if args.ipv4:
        public_ipv4 = get_public_ip(4)
        if public_ipv4:
            sync_dns_record(cf, zone_id, "A", hostname, public_ipv4)

    if args.ipv6:
        public_ipv6 = get_public_ip(6)
        if public_ipv6:
            sync_dns_record(cf, zone_id, "AAAA", hostname, public_ipv6)


if __name__ == "__main__":
    main()
