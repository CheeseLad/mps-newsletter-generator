import json
from jinja2 import Template
from lib.templates import start, end, end_after_social, html_template, social_template
from bs4 import BeautifulSoup
import sys
import os
import shutil
import zipfile
from config import social_data, image_mappings
import re
import datetime
from lib.postimages_login import login_to_postimages, get_api_key, upload_image
import hashlib
import string
import random

def load_image_cache():
    """Load the image upload cache from file"""
    cache_file = 'image_cache.json'
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load cache file: {e}")
    return {}

def save_image_cache(cache):
    """Save the image upload cache to file"""
    cache_file = 'image_cache.json'
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save cache file: {e}")

def get_file_hash(file_path):
    """Calculate SHA256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def generate_random_string(length=6):
    """Generate a random string of specified length"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def cleanup_temp_directory(tmp_dir):
    """Clean up temporary directory with retry logic for Windows and Google Drive"""
    import time
    
    for attempt in range(5):  # Try up to 5 times for Google Drive
        try:
            if os.path.exists(tmp_dir):
                # Force remove read-only files on Windows
                for root, dirs, files in os.walk(tmp_dir, topdown=False):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            os.chmod(file_path, 0o777)  # Make file writable
                        except:
                            pass
                    for dir in dirs:
                        dir_path = os.path.join(root, dir)
                        try:
                            os.chmod(dir_path, 0o777)  # Make directory writable
                        except:
                            pass
                
                # Try to remove the directory
                shutil.rmtree(tmp_dir, ignore_errors=True)
                
                # Check if directory still exists
                if not os.path.exists(tmp_dir):
                    print(f"✅ Cleaned up temporary directory: {tmp_dir}")
                    return True
                else:
                    # If directory still exists, try to remove individual files
                    print(f"⚠️ Directory still exists, trying individual file removal...")
                    for root, dirs, files in os.walk(tmp_dir, topdown=False):
                        for file in files:
                            try:
                                os.remove(os.path.join(root, file))
                            except:
                                pass
                        for dir in dirs:
                            try:
                                os.rmdir(os.path.join(root, dir))
                            except:
                                pass
                    # Final attempt to remove the directory
                    try:
                        os.rmdir(tmp_dir)
                        print(f"✅ Cleaned up temporary directory: {tmp_dir}")
                        return True
                    except:
                        pass
                        
        except Exception as e:
            if attempt < 4:  # Not the last attempt
                print(f"⚠️ Cleanup attempt {attempt + 1} failed, retrying in 2 seconds... ({e})")
                time.sleep(2)  # Wait longer for Google Drive sync
            else:
                print(f"❌ Failed to clean up temporary directory {tmp_dir} after 5 attempts: {e}")
                print(f"💡 You may need to manually delete: {tmp_dir}")
                return False
    return False

def main():
    zip_path = sys.argv[1]
    tmp_dir = f'./tmp_{generate_random_string(6)}'
    html_file_path = None

    os.makedirs(tmp_dir, exist_ok=True)
    print(f"Created temporary directory: {tmp_dir}")

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(tmp_dir)
        
    images_list = []
     
    for root, dirs, files in os.walk(tmp_dir):
        for file in files:
            if file.lower().endswith('.html'):
                html_file_path = os.path.join(root, file)
            elif file.lower().endswith('.png') or file.lower().endswith('.jpg') or file.lower().endswith('.jpeg') or file.lower().endswith('.gif'):
                images_list.append(os.path.join(root, file))
    
    # Load image cache
    print("=" * 50)
    print("Loading image cache...")
    image_cache = load_image_cache()
    print(f"Cache loaded with {len(image_cache)} entries")
    
    # Upload images to postimages.org
    print("=" * 50)
    print("Processing images for upload")
    print("=" * 50)
    
    # Check cache first, then upload if needed
    image_upload_mapping = {}
    images_to_upload = []
    
    # Add config images to the upload list
    config_images = []
    
    # Add header images from config
    for position, image_path in image_mappings.items():
        if os.path.exists(image_path):
            config_images.append((image_path, f"config_{position}"))
    
    # Add social icons from config
    for social in social_data:
        if os.path.exists(social["social_image"]):
            config_images.append((social["social_image"], f"config_social_{os.path.basename(social['social_image'])}"))
    
    # Combine zip images and config images
    all_images = [(path, os.path.basename(path)) for path in images_list] + config_images
    
    for image_path, original_filename in all_images:
        file_hash = get_file_hash(image_path)
        
        # Check if image is in cache with same hash
        if file_hash in image_cache:
            cached_url = image_cache[file_hash]
            image_upload_mapping[original_filename] = cached_url
            print(f"✅ Cached: {original_filename} -> {cached_url}")
        else:
            images_to_upload.append((image_path, original_filename, file_hash))
            print(f"📤 Need to upload: {original_filename}")
    
    # Upload new images if any
    if images_to_upload:
        print(f"\nUploading {len(images_to_upload)} new images...")
        
        # Login to postimages.org
        session = login_to_postimages()
        if not session:
            print("❌ Failed to login to postimages.org. Exiting.")
            return
        
        # Get API key
        api_key = get_api_key(session)
        if not api_key:
            print("❌ Failed to get API key. Exiting.")
            return
        
        # Upload new images
        for image_path, original_filename, file_hash in images_to_upload:
            print(f"\nUploading: {image_path}")
            upload_result = upload_image(session, api_key, image_path)
            if upload_result and upload_result.get('direct_link'):
                uploaded_url = upload_result['direct_link']
                image_upload_mapping[original_filename] = uploaded_url
                # Add to cache
                image_cache[file_hash] = uploaded_url
                print(f"✅ Uploaded: {original_filename} -> {uploaded_url}")
            else:
                print(f"❌ Failed to upload: {image_path}")
        
        # Save updated cache
        save_image_cache(image_cache)
        print(f"\nCache updated with {len(images_to_upload)} new entries")
    else:
        print("\n🎉 All images found in cache! No uploads needed.")
    
    print(f"\nTotal images processed: {len(image_upload_mapping)}")
    #print("Image mapping:", image_upload_mapping)
    
    # Update image_mappings with uploaded URLs for config images
    updated_image_mappings = image_mappings.copy()
    for position, local_path in image_mappings.items():
        config_key = f"config_{position}"
        if config_key in image_upload_mapping:
            updated_image_mappings[position] = image_upload_mapping[config_key]
            print(f"✅ Updated mapping: {position} -> {image_upload_mapping[config_key]}")
    
    # Update social_data with uploaded URLs
    updated_social_data = []
    for social in social_data:
        updated_social = social.copy()
        local_path = social["social_image"]
        config_key = f"config_social_{os.path.basename(local_path)}"
        if config_key in image_upload_mapping:
            updated_social["social_image"] = image_upload_mapping[config_key]
            print(f"✅ Updated social: {os.path.basename(local_path)} -> {image_upload_mapping[config_key]}")
        updated_social_data.append(updated_social)
                
    finished_html = generate_email(html_file_path, image_upload_mapping, updated_image_mappings, updated_social_data)
    #print(images_list)
    
    # Clean up temporary directory
    cleanup_temp_directory(tmp_dir)

def generate_email(html_file_path, image_upload_mapping=None, updated_image_mappings=None, updated_social_data=None):
    with open(html_file_path, "r", encoding="utf-8") as file:
        content = file.read()
        
        # Replace local image paths with uploaded URLs if mapping is provided
        if image_upload_mapping:
            for local_filename, uploaded_url in image_upload_mapping.items():
                # Replace various possible image path patterns
                content = content.replace(f'src="images/{local_filename}"', f'src="{uploaded_url}"')
                content = content.replace(f'src="tmp/images/{local_filename}"', f'src="{uploaded_url}"')
                content = content.replace(f'src="./images/{local_filename}"', f'src="{uploaded_url}"')
                content = content.replace(f'src="../images/{local_filename}"', f'src="{uploaded_url}"')
                print(f"Replaced image reference: {local_filename} -> {uploaded_url}")
        else:
            # Fallback to original behavior
            content = content.replace('src="images/image', 'src="tmp/images/image')
        data_content = content.split("<body>")[0].split("</body>")[0]
        sections = re.split(r'<p class="c\d+"><span class="c\d+">&mdash; ', data_content)
        print("Total sections found:", len(sections))
        
        position_content_list = []
        
        for i in range(1, len(sections)):
            section_content = sections[i].split("</span>")[0].strip().replace(" ", "-").lower()  # Get the content, clean up
            print("Processing section:", section_content)
            cool = "".join(sections[i].split("</span>")[1:])  # Print the content after </span>
            
            soup = BeautifulSoup(cool, "html.parser")  # Parse the HTML content
            
            len_cool = soup.get_text(strip=True)  # Get the text content without HTML tags        
            
            # Correcting the structure to match our expected dictionary
            position_content_list.append({
                "position": section_content,  # Assuming the first word is the position
                "content": cool,
                "length": len(len_cool)  # Length of the content
            })
        
        # Creating the final structure
        final_data = {
            "total_sections": len(position_content_list),
            "sections": position_content_list
        }

    # Output the result as a JSON formatted string
    json_output = json.dumps(final_data, indent=4)
    

    # Printing the generated JSON output
    #print(json_output)

    # Jinja2 template for rendering the HTML
    
    # Initialize the Jinja2 template engine
    template = Template(html_template)
    socials = Template(social_template)
    start_template = Template(start)
    end_template = Template(end)
    
    # Use updated mappings if provided, otherwise use original
    final_image_mappings = updated_image_mappings if updated_image_mappings else image_mappings
    final_social_data = updated_social_data if updated_social_data else social_data

    # Render HTML for each section in the JSON data
    rendered_html = ""
    email_subject_text = ""
    email_start_text = ""
    email_end_text = ""
    for section in final_data["sections"]:
        # Ensure section is a dictionary and access its keys properly
        #print(image_mappings.get(section["position"], ""))
        if (isinstance(section, dict) and "content" in section) and section["length"] > 0 and section["position"] not in ["email-start", "email-end", "email-subject"]:
            # Pass the section content into the template as "styledContent"
            print("Processing section:", section["position"])
            rendered_html += template.render(styledContent=section["content"], header_image=final_image_mappings.get(section["position"], ""))
        elif section["position"] == "email-start" or section["position"] == "email-end" or section["position"] == "email-subject":
            if section["position"] == "email-start":
                email_start_text = section["content"]
            elif section["position"] == "email-end":
                email_end_text = section["content"]
            elif section["position"] == "email-subject":
                email_subject_text = section["content"]
        else:
            if section["length"] == 0:
                print(f"Skipping section: {section['position']} (not filled in)")
            else:
                print("Skipping invalid section:", section)
            


    social_html = ""

    for social in final_social_data:
        social_html += socials.render(
            social_link=social["social_link"],
            social_image=social["social_image"]
        )
        
    # Extract plain text from email_subject_text for the title tag
    email_subject_plain_text = ""
    if email_subject_text:
        soup = BeautifulSoup(email_subject_text, 'html.parser')
        email_subject_plain_text = soup.get_text().strip()
    
    start_html = start_template.render(
        email_start=email_start_text,
        header_image=final_image_mappings.get("logo"),
        email_subject=email_subject_plain_text
    )
    
    start_html = start_html.replace('<p class=', '<p dir="ltr" style="color: #F2F2F2;font-family: Helvetica;font-size: 14px;font-weight: bold;text-align: center;margin: 10px 0;padding: 0;mso-line-height-rule: exactly;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%;line-height: 150%;" class=')

    end_html = end_template.render(
        email_end=email_end_text
    )
    
    end_html = end_html.replace('<p class=', '<p dir="ltr" style="color: #F2F2F2;font-family: Helvetica;font-size: 14px;font-weight: bold;text-align: center;margin: 10px 0;padding: 0;mso-line-height-rule: exactly;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%;line-height: 150%;" class=')

        
    # Output the rendered HTML
    #print(rendered_html)
    current_datetime = datetime.datetime.now()
    current_date = current_datetime.strftime("%Y-%m-%d")
    current_time = current_datetime.strftime("%H-%M-%S")
    
    # Create emails directory if it doesn't exist
    emails_dir = "emails"
    os.makedirs(emails_dir, exist_ok=True)
    
    filename = f"mps-email-{current_date}-{current_time}.html"
    filepath = os.path.join(emails_dir, filename)
    
    with open(filepath, "w") as output_file:

        rendered_html = rendered_html.replace('<p class=', '<p dir="ltr" style="color: #F2F2F2;font-family: Helvetica;font-size: 14px;font-weight: bold;text-align: center;margin: 10px 0;padding: 0;mso-line-height-rule: exactly;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%;line-height: 150%;" class=')
    
        output_file.write(start_html + rendered_html + end_html + social_html + end_after_social)


    print(f"HTML file generated successfully as {filepath}")
    return rendered_html


if __name__ == "__main__":
    main()