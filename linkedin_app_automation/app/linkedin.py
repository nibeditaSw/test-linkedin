import requests
import logging
import json

logger = logging.getLogger(__name__)
session = requests.Session()

def get_linkedin_user_id(access_token):
    """Fetch LinkedIn user ID using the /rest/me API."""
    if not access_token:
        logger.error("LinkedIn access token is empty.")
        return None
    url = "https://api.linkedin.com/rest/me"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202306"
    }
    logger.debug(f"Sending GET request to {url}, Token (masked): {access_token[:10]}...")
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        user_data = response.json()
        user_id = user_data.get("id")
        if not user_id:
            logger.error("No 'id' found in LinkedIn /rest/me response.")
            return None
        logger.info(f"Fetched LinkedIn user ID: {user_id}")
        return user_id
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching LinkedIn user ID: {e}, Status: {response.status_code}, Response: {response.text}")
        return None
    except Exception as e:
        logger.error(f"Error fetching LinkedIn user ID: {e}")
        return None

def register_image_upload(access_token, user_id):
    """Register an image upload with LinkedIn API."""
    url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202306"
    }
    payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": f"urn:li:person:{user_id}",
            "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
        }
    }
    logger.debug(f"Registering image upload, payload: {json.dumps(payload, indent=2)}...")
    try:
        response = session.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        upload_url = data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn = data["value"]["asset"]
        media_artifact = data["value"]["mediaArtifact"]
        logger.info(f"Registered image upload, uploadUrl: {upload_url[:50]}..., asset: {asset_urn}")
        return upload_url, asset_urn, media_artifact
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error registering image upload: {e}, Status: {response.status_code}, Response: {response.text}")
        return None, None, None
    except Exception as e:
        logger.error(f"Error registering image upload: {e}")
        return None, None, None

def upload_image(image_url, upload_url, access_token):
    """Upload image binary to LinkedIn using the upload URL."""
    logger.debug(f"Fetching image from {image_url} for upload...")
    try:
        response = session.get(image_url, timeout=10)
        response.raise_for_status()
        headers = {"Authorization": f"Bearer {access_token}"}
        upload_response = session.post(upload_url, headers=headers, data=response.content, timeout=10)
        upload_response.raise_for_status()
        logger.info(f"Successfully uploaded image from {image_url}")
        return True
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error uploading image: {e}, Status: {upload_response.status_code}, Response: {upload_response.text}")
        return False
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        return False

def post_to_linkedin(post_text, access_token, user_id, image_url=None):
    """Post content with optional image to LinkedIn using v2/ugcPosts."""
    if image_url:
        upload_url, asset_urn, media_artifact = register_image_upload(access_token, user_id)
        if not upload_url or not asset_urn:
            logger.error("Failed to register image upload.")
            return False
        if not upload_image(image_url, upload_url, access_token):
            logger.error("Failed to upload image.")
            return False
        media = [{
            "status": "READY",
            "media": asset_urn,
            "title": {"text": "Shared Image"},
            "description": {"text": "Image attached to post"}
        }]
        share_media_category = "IMAGE"
    else:
        media = []
        share_media_category = None

    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202306"
    }
    payload = {
        "author": f"urn:li:person:{user_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_text},
                "shareMediaCategory": share_media_category,
                "media": media if image_url else []
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    logger.debug(f"Sending POST request to {url}, payload: {json.dumps(payload, indent=2)}...")
    try:
        response = session.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully posted to LinkedIn with{'out' if not image_url else''} image: {post_text[:50]}...")
        return True
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error posting to LinkedIn: {e}, Status: {response.status_code}, Response: {response.text}")
        return False
    except Exception as e:
        logger.error(f"Error posting to LinkedIn: {e}")
        return False
