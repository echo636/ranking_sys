import requests
import json
import sys

# Test URL ranking endpoint
payload = {
    "task_description": "比较这些技术文章的质量、深度和实用性",
    "urls": [
        "https://example.com",
        "https://www.wikipedia.org",
        "https://github.com"
    ]
}

def test_url_ranking():
    url = "http://localhost:8000/api/v1/rank-urls"
    print(f"Sending URL ranking request to {url}...")
    print(f"URLs to compare: {payload['urls']}")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        print("\n=== Success! Response ===")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Is it running?")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response Body: {response.text}")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("Error: Request timed out (60s). This is normal for URL scraping.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_url_ranking()
