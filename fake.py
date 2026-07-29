from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import json
import re
import html

app = FastAPI(title="Fake Profile & Link Detector")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScanRequest(BaseModel):
    url: str
    mode: str = "auto"


SOCIAL_MEDIA_PATTERN = re.compile(r"(instagram\.com|twitter\.com|x\.com|facebook\.com|tiktok\.com|linkedin\.com)")
SUSPICIOUS_KEYWORDS = ["bot", "fake", "free", "gift", "claim", "verify", "login", "click", "winner", "earn"]
SHORTENERS = ["bit.ly", "tinyurl.com", "t.co", "ow.ly", "goo.gl"]


def extract_username_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if "instagram.com" in host:
        return path.split("/")[0] if path else ""
    if "twitter.com" in host or "x.com" in host:
        return path.split("/")[0] if path else ""
    return ""


def parse_instagram_profile_payload(payload: dict) -> dict:
    user = payload.get("graphql", {}).get("user", {})
    return {
        "followers": user.get("edge_followed_by", {}).get("count"),
        "following": user.get("edge_follow", {}).get("count"),
        "created_at": user.get("created_at") or "Unavailable",
        "privacy": "Public" if user.get("is_private") is False else "Private" if user.get("is_private") is True else "Unknown",
    }


def parse_twitter_profile_payload(payload: list | dict) -> dict:
    if isinstance(payload, list) and payload:
        item = payload[0]
        return {
            "followers": item.get("followers_count"),
            "following": item.get("friends_count"),
            "created_at": item.get("created_at") or "Unavailable",
            "privacy": "Unknown",
        }
    if isinstance(payload, dict):
        return {
            "followers": payload.get("followers_count"),
            "following": payload.get("friends_count"),
            "created_at": payload.get("created_at") or "Unavailable",
            "privacy": "Unknown",
        }
    return {"followers": None, "following": None, "created_at": "Unavailable", "privacy": "Unknown"}


def parse_instagram_html(html_text: str) -> dict:
    patterns = [
        r'"edge_followed_by"\s*:\s*\{"count":\s*(\d+)',
        r'"edge_follow"\s*:\s*\{"count":\s*(\d+)',
        r'"date_created"\s*:\s*"([^"]+)"',
    ]
    followers = None
    following = None
    created_at = "Unavailable"

    match = re.search(patterns[0], html_text)
    if match:
        followers = int(match.group(1))
    match = re.search(patterns[1], html_text)
    if match:
        following = int(match.group(1))
    match = re.search(patterns[2], html_text)
    if match:
        created_at = html.unescape(match.group(1))

    return {"followers": followers, "following": following, "created_at": created_at, "privacy": "Unknown"}


def parse_twitter_html(html_text: str) -> dict:
    followers = None
    following = None
    created_at = "Unavailable"

    follower_match = re.search(r'followers_count\":(\d+)', html_text)
    if follower_match:
        followers = int(follower_match.group(1))
    following_match = re.search(r'friends_count\":(\d+)', html_text)
    if following_match:
        following = int(following_match.group(1))
    created_match = re.search(r'created_at\":\"([^\"]+)\"', html_text)
    if created_match:
        created_at = html.unescape(created_match.group(1))
    return {"followers": followers, "following": following, "created_at": created_at, "privacy": "Unknown"}


def fetch_profile_metadata(url: str) -> dict:
    target = url.strip()
    username = extract_username_from_url(target)
    if not username:
        return {"followers": None, "following": None, "created_at": "Unavailable", "privacy": "Unknown"}

    parsed = urlparse(target)
    host = parsed.netloc.lower()

    endpoints = []
    if "instagram.com" in host:
        endpoints = [
            f"https://www.instagram.com/{username}/?__a=1",
            f"https://www.instagram.com/{username}/",
        ]
    elif "twitter.com" in host or "x.com" in host:
        endpoints = [
            f"https://cdn.syndication.twimg.com/widgets/followbutton/info.json?screen_names={username}",
            f"https://twitter.com/{username}",
        ]

    for endpoint in endpoints:
        request = Request(endpoint, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(request, timeout=12) as response:
                body = response.read().decode("utf-8", "ignore")
                if "instagram.com" in host:
                    data = json.loads(body) if body.lstrip().startswith("{") else None
                    if isinstance(data, dict):
                        return parse_instagram_profile_payload(data)
                    parsed_html = parse_instagram_html(body)
                    if parsed_html["followers"] is not None or parsed_html["following"] is not None:
                        return parsed_html
                elif "twitter.com" in host or "x.com" in host:
                    try:
                        data = json.loads(body)
                        return parse_twitter_profile_payload(data)
                    except (ValueError, json.JSONDecodeError):
                        parsed_html = parse_twitter_html(body)
                        if parsed_html["followers"] is not None or parsed_html["following"] is not None:
                            return parsed_html
        except (URLError, HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
            continue

    return {"followers": None, "following": None, "created_at": "Unavailable", "privacy": "Unknown"}


def analyze_profile(url: str) -> dict:
    target = url.strip().lower()
    metadata = fetch_profile_metadata(url)
    if not target:
        return {"status": "Unknown", "reason": "Please enter a profile URL.", "metadata": metadata}

    if not target.startswith(("http://", "https://")):
        return {
            "status": "Suspicious",
            "reason": "This does not look like a valid web profile URL. Add the full link including http:// or https://.",
            "metadata": metadata,
        }

    if any(word in target for word in ["bot", "fake", "free", "claim", "winner", "earn"]):
        return {
            "status": "Suspicious",
            "reason": "The profile link contains suspicious words often used in fake or spam accounts.",
            "metadata": metadata,
        }

    if SOCIAL_MEDIA_PATTERN.search(target):
        return {
            "status": "Safe",
            "reason": "The profile URL points to a familiar social platform and does not show obvious fake-account indicators.",
            "metadata": metadata,
        }

    return {
        "status": "Suspicious",
        "reason": "The profile URL does not match a known social profile pattern, so it should be treated carefully.",
        "metadata": metadata,
    }


def analyze_link(url: str) -> dict:
    target = url.strip().lower()
    if not target:
        return {"status": "Unknown", "reason": "Please enter a link to check."}

    if not target.startswith(("http://", "https://")):
        return {
            "status": "Suspicious",
            "reason": "The link is incomplete. Use a full URL with http:// or https://.",
        }

    parsed = urlparse(target)
    domain = parsed.netloc.lower()

    if target.startswith("http://"):
        return {
            "status": "Suspicious",
            "reason": "The link uses HTTP instead of HTTPS, which is unsafe and often used by phishing pages.",
        }

    if any(shortener in domain for shortener in SHORTENERS):
        return {
            "status": "Suspicious",
            "reason": "The link uses a URL shortener, which can hide the real destination.",
        }

    if any(word in target for word in SUSPICIOUS_KEYWORDS):
        return {
            "status": "Suspicious",
            "reason": "The link contains words commonly used in phishing or scam messages.",
        }

    return {
        "status": "Safe",
        "reason": "The link uses HTTPS and does not show obvious phishing indicators.",
    }


@app.get("/")
async def home():
    return FileResponse("fake.html")


@app.post("/api/scan")
async def scan_target(request: ScanRequest):
    target = request.url.strip()
    mode = request.mode.lower()

    if mode == "profile":
        engine_used = "Profile Engine"
        result = analyze_profile(target)
    elif mode == "link":
        engine_used = "Link Engine"
        result = analyze_link(target)
    else:
        if SOCIAL_MEDIA_PATTERN.search(target):
            engine_used = "Profile Engine"
            result = analyze_profile(target)
        else:
            engine_used = "Link Engine"
            result = analyze_link(target)

    return {
        