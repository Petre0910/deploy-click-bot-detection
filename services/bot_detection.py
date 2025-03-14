from user_agents import parse
import requests
from services.database import get_click_stats

def is_bot(ip, user_agent, headers, email_id, db):
    ua = parse(user_agent or "")

    # Handle IP info request safely
    try:
        ipinfo_response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=3)
        ip_data = ipinfo_response.json()
    except requests.RequestException:
        ip_data = {}

    # 1. Known bot signatures
    bot_keywords = ["bot", "spider", "crawler", "scan", "python-requests", "wget", "curl"]
    if any(keyword in (user_agent or "").lower() for keyword in bot_keywords):
        return True, "User-Agent matches known bots"

    # 2. Check essential headers
    expected_headers = ["accept", "accept-language", "user-agent", "accept-encoding", "connection"]
    headers_lower = {k.lower(): v for k, v in headers.items()}
    missing_headers = [h for h in expected_headers if h not in headers_lower]
    if missing_headers:
        return True, f"Missing essential headers: {', '.join(missing_headers)}"

    # 3. Check for modern browser headers
    if not headers_lower.get("sec-ch-ua", "") or not headers_lower.get("sec-fetch-site", ""):
        return True, "Missing 'sec-ch-ua' or 'sec-fetch-site' headers, likely bot."

    # 4. Suspicious Accept header
    accept = headers_lower.get("accept", "")
    if "*/*" in accept and "text/html" not in accept:
        return True, "Suspicious Accept header prioritizing */* without text/html."

    # 5. Headless or mobile emulators
    if ua.is_bot or not ua.is_pc:
        return True, "Likely a headless browser or mobile emulator"

    # 6. IP from cloud providers or VPNs
    org_info = (ip_data.get("org", "") + " " + ip_data.get("asn", {}).get("description", "")).lower()
    cloud_keywords = ["google", "amazonaws", "cloudflare", "microsoft", "digitalocean", "linode", "ovh", "hosting", "vpn"]
    if any(keyword in org_info for keyword in cloud_keywords):
        return True, "IP belongs to a known hosting provider or VPN"

    # 7. Unusual click behavior
    same_time_email_count, _ = get_click_stats(email_id, db)
    if same_time_email_count > 3:
        return True, "Unusual click behavior detected!"

    # All checks passed
    return False, None
