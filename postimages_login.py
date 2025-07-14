import requests
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import base64
import xml.etree.ElementTree as ET
import time
import random

# Load environment variables from .env file
load_dotenv()

def extract_csrf_token(html_content):
    """Extract CSRF token from HTML content using BeautifulSoup"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for input field with name="csrf_hash"
    csrf_input = soup.find('input', {'name': 'csrf_hash'})
    if csrf_input and csrf_input.get('value'):
        return csrf_input['value']
    
    return None

def extract_api_key(html_content):
    """Extract API key from HTML content using BeautifulSoup"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for input field with id="api_key"
    api_input = soup.find('input', {'id': 'api_key'})
    if api_input and api_input.get('value'):
        return api_input['value']
    
    # Fallback: look for input field with name="api_key"
    api_input = soup.find('input', {'name': 'api_key'})
    if api_input and api_input.get('value'):
        return api_input['value']
    
    return None

def login_to_postimages():
    # Login URL
    url = "https://postimages.org/login"
    
    # Load credentials from environment variables
    email = os.getenv('POSTIMAGES_EMAIL')
    password = os.getenv('POSTIMAGES_PASSWORD')
    
    # Check if credentials are provided
    if not email or not password:
        print("❌ Error: Please set environment variables:")
        print("   POSTIMAGES_EMAIL=your_email@example.com")
        print("   POSTIMAGES_PASSWORD=your_password")
        return None
    
    print(f"✅ Using email: {email}")
    
    # Headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        # Create a session to maintain cookies
        session = requests.Session()
        
        # First, get the login page to establish session and extract CSRF token
        print("Getting login page...")
        response = session.get(url, headers=headers)
        print(f"Login page status: {response.status_code}")
        
        # Extract CSRF token from the login page
        print("Extracting CSRF token...")
        csrf_token = extract_csrf_token(response.text)
        
        if not csrf_token:
            print("❌ Could not extract CSRF token from login page")
            return None
        
        print(f"✅ Extracted CSRF token: {csrf_token[:10]}...")
        
        # Prepare form data with extracted CSRF token
        form_data = {
            'csrf_hash': csrf_token,
            'email': email,
            'password': password
        }
        
        # Now perform the login POST request
        print("\nAttempting login...")
        login_response = session.post(url, data=form_data, headers=headers)
        
        print(f"Login response status: {login_response.status_code}")
        print(f"Login response URL: {login_response.url}")
        print(f"Response headers: {dict(login_response.headers)}")
        
        if login_response.status_code == 200:
            if email in login_response.text:
                print(f"\n✅ Login successful! Found email '{email}' in response.")
            else:
                print(f"\n❌ Login failed - email '{email}' not found in response.")
        else:
            print(f"\n❌ Login failed with status code: {login_response.status_code}")
            
        return session
        
    except requests.exceptions.RequestException as e:
        print(f"Error during login: {e}")
        return None

def get_api_key(session):
    """Get API key from postimages.org API page"""
    if not session:
        print("❌ Error: No authenticated session provided")
        return None
    
    api_url = "https://postimages.org/login/api"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        print("Getting API key page...")
        response = session.get(api_url, headers=headers)
        print(f"API page status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Failed to get API page: {response.status_code}")
            return None
        
        # Extract API key from the page
        print("Extracting API key...")
        api_key = extract_api_key(response.text)
        
        if not api_key:
            print("❌ Could not extract API key from page")
            return None
        
        print(f"✅ API Key: {api_key}")
        return api_key
        
    except requests.exceptions.RequestException as e:
        print(f"Error getting API key: {e}")
        return None

def upload_image(session, api_key, image_path):
    """Upload a local image file to postimages.org using the plugin method and authenticated session."""
    if not session:
        print("❌ Error: No authenticated session provided")
        return None
    if not api_key:
        print("❌ Error: No API key provided")
        return None
    if not os.path.exists(image_path):
        print(f"❌ Error: Image file not found: {image_path}")
        return None

    upload_url = "https://postimages.org/json/rr"
    upload_data = {
        'token': api_key,
        'optsize': '0',
        'expire': '0',
        'session_upload': str(int(time.time() * 1000)),
        'numfiles': '1',
        'upload_session': ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=32))
    }

    print(f"Uploading image: {image_path}")
    with open(image_path, 'rb') as image_file:
        files = {
            'file': (os.path.basename(image_path), image_file, 'image/*')
        }
        # DO NOT set Content-Type header for multipart!
        response = session.post(upload_url, data=upload_data, files=files)

    print(f"Upload response status: {response.status_code}")
    if response.status_code == 200:
        try:
            result = response.json()
            print("✅ Upload successful!")
            print(f"Response: {result}")
            if result.get('status') == 'OK' and 'url' in result:
                image_url = result['url']
                print(f"📁 File uploaded successfully! URL: {image_url}")
                # Now get the direct image URL from the page
                direct_url = extract_direct_image_url(image_url)
                if direct_url:
                    print(f"   Direct URL: {direct_url}")
                    return {'url': image_url, 'direct_link': direct_url}
                else:
                    print("⚠️ Could not extract direct URL")
                    return {'url': image_url}
            else:
                print(f"❌ Upload failed: {result}")
                return None
        except Exception as e:
            print(f"❌ Failed to parse JSON response: {e}")
            print(f"Response text: {response.text[:200]}")
            return None
    else:
        print(f"❌ Upload failed with status code: {response.status_code}")
        print(f"Response text: {response.text[:200]}")
        return None

def extract_direct_image_url(image_url):
    """Extract direct image URL from the postimages.org page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(image_url, headers=headers)
        if response.status_code == 200:
            # Look for og:image meta tag
            soup = BeautifulSoup(response.text, 'html.parser')
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                return og_image['content']
            
            # Fallback: look for direct image link
            direct_link = soup.find('a', {'id': 'download'})
            if direct_link and direct_link.get('href'):
                return direct_link['href']
        
        return None
    except Exception as e:
        print(f"Error extracting direct URL: {e}")
        return None

if __name__ == "__main__":
    print("PostImages Login Script")
    print("=" * 30)
    session = login_to_postimages()
    
    if session:
        print("\n" + "=" * 30)
        print("Getting API Key")
        print("=" * 30)
        api_key = get_api_key(session)
        
        if api_key:
            print(f"\n🎉 Success! Your API key is: {api_key}")
            
            # Test upload with a sample image
            print("\n" + "=" * 30)
            print("Testing Image Upload")
            print("=" * 30)
            
            # Try to upload one of the header images
            test_image_path = "assets/header_images/1.png"
            if os.path.exists(test_image_path):
                upload_result = upload_image(session, api_key, test_image_path)
                if upload_result:
                    print(f"\n🎉 Image upload successful!")
                    print(f"   Direct URL: {upload_result.get('direct_link', 'N/A')}")
                else:
                    print("\n❌ Image upload failed")
            else:
                print(f"❌ Test image not found: {test_image_path}")
                print("   Please provide a valid image path to test upload")
        else:
            print("\n❌ Failed to get API key") 