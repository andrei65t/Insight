"""
OpenRouter API Key Usage Checker
=================================
Enter your OpenRouter API key and see how much you've spent so far,
your remaining credits, and rate limit info.

Usage:
    python scripts/openrouter_cost_check.py

    Or pass the key directly:
    python scripts/openrouter_cost_check.py sk-or-v1-...

Requires: requests  (pip install requests)
"""

import sys
import requests

BASE_URL = "https://openrouter.ai/api/v1"


def get_key_info(api_key: str) -> dict:
    """Query OpenRouter for key usage and credit info."""
    r = requests.get(
        f"{BASE_URL}/auth/key",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def format_usd(value) -> str:
    if value is None:
        return "N/A"
    return f"${float(value):.4f}"


def main():
    # Get key from argument or prompt
    # if len(sys.argv) > 1:
    #     api_key = sys.argv[1].strip()
    # else:
    #     api_key = input("\n  Enter your OpenRouter API key: ").strip()

    api_key = "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"

    if not api_key:
        print("  ERROR: No API key provided.")
        sys.exit(1)

    print("\n  Checking key usage...\n")

    try:
        resp = get_key_info(api_key)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("  ERROR: Invalid API key. Double-check and try again.")
        elif e.response.status_code == 403:
            print("  ERROR: Key does not have permission to query usage.")
        else:
            print(f"  ERROR: HTTP {e.response.status_code} — {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    data = resp.get("data", resp)

    # Extract fields — OpenRouter returns different structures depending
    # on key type, so we handle both common shapes gracefully.
    label = data.get("label", "Unknown")
    usage = data.get("usage", 0)
    limit = data.get("limit", None)
    is_free_tier = data.get("is_free_tier", None)
    rate_limit = data.get("rate_limit", {})

    usage_val = float(usage) if usage else 0.0
    limit_val = float(limit) if limit else None
    remaining = (limit_val - usage_val) if limit_val is not None else None

    # Display
    print("  " + "=" * 52)
    print("    OpenRouter API Key Usage Report")
    print("  " + "=" * 52)
    print(f"    Key label:       {label}")
    print(f"    Total spent:     {format_usd(usage_val)}")
    print(f"    Credit limit:    {format_usd(limit_val) if limit_val is not None else 'Unlimited'}")
    if remaining is not None:
        print(f"    Remaining:       {format_usd(remaining)}")
        # Visual bar
        pct_used = min(usage_val / limit_val * 100, 100) if limit_val else 0
        bar_len = 30
        filled = int(bar_len * pct_used / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"    Usage:           [{bar}] {pct_used:.1f}%")

    if is_free_tier is not None:
        print(f"    Free tier:       {'Yes' if is_free_tier else 'No'}")

    if rate_limit:
        print(f"\n    Rate limits:")
        print(f"      Requests:      {rate_limit.get('requests', 'N/A')}")
        print(f"      Interval:      {rate_limit.get('interval', 'N/A')}")

    print("\n  " + "-" * 52)
    print(f"    Key (masked):    {api_key[:12]}...{api_key[-4:]}")
    print(f"    Browse pricing:  https://openrouter.ai/models")
    print("  " + "-" * 52)
    print()


if __name__ == "__main__":
    main()
