from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import uvicorn

app = FastAPI(title="Fake Profile Detector")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

social_pattern = r"(instagram\.com|twitter\.com|x\.com|facebook\.com|tiktok\.com|linkedin\.com)"
suspicious_words = ["bot", "fake", "free", "gift", "claim", "verify", "login", "click", "winner", "earn"]
shorteners = ["bit.ly", "tinyurl.com", "t.co", "ow.ly", "goo.gl"]


class ScanRequest(BaseModel):
    url: str
    mode: str = "auto"


def analyze_url(url: str, mode: str = "auto") -> dict:
    target = url.strip().lower()

    if not target:
        return {"engine": "Local Analysis", "status": "Unknown", "reason": "Please enter a URL or profile link."}

    if not target.startswith(("http://", "https://")):
        return {"engine": "Local Analysis", "status": "Suspicious", "reason": "This does not look like a complete web address. Add http:// or https://."}

    import re

    if mode == "profile":
        if any(word in target for word in suspicious_words):
            return {"engine": "Profile Engine", "status": "Suspicious", "reason": "The profile link contains words often used in fake or spam accounts."}
        if re.search(social_pattern, target):
            return {"engine": "Profile Engine", "status": "Safe", "reason": "The profile URL points to a familiar social platform and looks normal."}
        return {"engine": "Profile Engine", "status": "Suspicious", "reason": "The profile URL does not match a known social pattern, so it should be treated carefully."}

    if mode == "link":
        if target.startswith("http://"):
            return {"engine": "Link Engine", "status": "Suspicious", "reason": "The link uses HTTP instead of HTTPS, which is unsafe and often used by phishing pages."}
        if any(shortener in target for shortener in shorteners):
            return {"engine": "Link Engine", "status": "Suspicious", "reason": "The link uses a URL shortener, which can hide the real destination."}
        if any(word in target for word in suspicious_words):
            return {"engine": "Link Engine", "status": "Suspicious", "reason": "The link contains words commonly used in phishing or scam messages."}
        return {"engine": "Link Engine", "status": "Safe", "reason": "The link uses HTTPS and does not show obvious phishing indicators."}

    if re.search(social_pattern, target):
        return {"engine": "Profile Engine", "status": "Safe", "reason": "The target appears to be a familiar social profile URL."}

    if target.startswith("http://"):
        return {"engine": "Link Engine", "status": "Suspicious", "reason": "The link uses HTTP instead of HTTPS, which is unsafe and often used by phishing pages."}
    if any(shortener in target for shortener in shorteners):
        return {"engine": "Link Engine", "status": "Suspicious", "reason": "The link uses a URL shortener, which can hide the real destination."}
    if any(word in target for word in suspicious_words):
        return {"engine": "Link Engine", "status": "Suspicious", "reason": "The link contains words commonly used in phishing or scam messages."}

    return {"engine": "Link Engine", "status": "Safe", "reason": "The link uses HTTPS and does not show obvious phishing indicators."}


@app.get("/")
async def home():
    return FileResponse(Path(__file__).resolve().parent / "fake.html")


@app.post("/api/scan")
def scan(req: ScanRequest):
    return analyze_url(req.url, req.mode)


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
