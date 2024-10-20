# pyflared-ddns

A DynDNS-client written in Python to sync your device's public IPv6 and IPv4 addresses with Cloudflare DNS entries.

This can be useful for home servers in scenarios where you want to make your self-hosted services available through a domain that's cofigurable through Cloudflare but your ISP will assign you a new IP address periodically.

## Getting started

### Install dependencies

This script relies on a few modules to function properly.
To install these, first clone this repository and `cd` into its directory. From here, run the following:
> `pip install -r requirements.txt`

### Copy and fill out .env file

Next, copy or rename the config file like this:
>`$ cp .env.example .env`

Afterwards, edit `.env` with your preferred text editor and fill in the needed variables
You will need:

- `CF_TOKEN`: This will hold your Cloudflare API token to read and edit the needed DNS entries. This token will need _Edit_ permissions for the DNS zone it needs to edit.
- `CF_HOSTNAME`: Your domain name on Cloudflare to keep up-to-date, this can be _example.com_ for example
- `CF_ZONE-ID`: This is your zone's ID, it can be accessed through the righthand-side menu on the overview page of your DNS zone under _API -> Zone ID_

### Set up cron job

To have your server regularly check and, if neccessary, update its DNS records, create a cron job that executes this script in certain intervals.
You can do so by running `crontab -e` and inserting the following:
> `*/10 * * * * /usr/bin/python3 /your/path/pyflared-ddns/main.py`

In this example we're running the script every ten minutes.

## Logging

This script, by default, logs updates into the subfolder `logs`.

## Arguments

This script will, by default, create and update both A and AAAA records for your domain.
If you can't (or don't want to) use either of these, you can run this script with either `--ipv4` or `--ipv6` as arguments. Specifying these will **only** update the given IP version's address.
