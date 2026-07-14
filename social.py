import os
import logging
import httpx
from database import get_social_accounts

logger = logging.getLogger(__name__)

FACEBOOK_API = "https://graph.facebook.com/v22.0"
TIKTOK_API = "https://open-api.tiktok.com"

async def post_to_facebook(user_id: int, message: str) -> str:
    accounts = get_social_accounts(user_id)
    fb = next((a for a in accounts if a["platform"] == "facebook"), None)
    if not fb:
        return "Facebook not connected. Use /connect facebook <token>"
    
    page_id = fb.get("page_id")
    token = fb["access_token"]
    
    async with httpx.AsyncClient() as client:
        if page_id:
            url = f"{FACEBOOK_API}/{page_id}/feed"
        else:
            url = f"{FACEBOOK_API}/me/feed"
        r = await client.post(url, data={"message": message, "access_token": token})
        data = r.json()
        if "id" in data:
            return f"Posted to Facebook! (ID: {data['id']})"
        return f"Facebook error: {data.get('error', {}).get('message', 'Unknown')}"

async def post_to_tiktok(user_id: int, message: str) -> str:
    accounts = get_social_accounts(user_id)
    tt = next((a for a in accounts if a["platform"] == "tiktok"), None)
    if not tt:
        return "TikTok not connected. Use /connect tiktok <token>"
    
    return "TikTok posting requires video upload via their API. Text-only not supported yet."

async def post_to_social(user_id: int, platform: str, message: str) -> str:
    if platform == "facebook":
        return await post_to_facebook(user_id, message)
    elif platform == "tiktok":
        return await post_to_tiktok(user_id, message)
    return f"Platform '{platform}' not supported. Use 'facebook' or 'tiktok'."
