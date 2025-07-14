import json
from jinja2 import Template
from templates import start, end, end_after_social, html_template, social_template
from bs4 import BeautifulSoup
import sys
import os
import shutil
import zipfile
from config import social_data, image_mappings
import re
import datetime

def main():
    zip_path = sys.argv[1]
    tmp_dir = './tmp'
    html_file_path = None

    os.makedirs(tmp_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(tmp_dir)
        
    images_list = []
     
    for root, dirs, files in os.walk(tmp_dir):
        for file in files:
            if file.lower().endswith('.html'):
                html_file_path = os.path.join(root, file)
            elif file.lower().endswith('.png') or file.lower().endswith('.jpg') or file.lower().endswith('.jpeg') or file.lower().endswith('.gif'):
                images_list.append(os.path.join(root, file))
                
    finished_html = generate_email(html_file_path)
    print(images_list)

def generate_email(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as file:
        content = file.read()
        content = content.replace('src="images/image', 'src="tmp/images/image')
        data_content = content.split("<body>")[0].split("</body>")[0]
        sections = re.split(r'<p class="c\d+"><span class="c\d+ c\d+">&mdash; ', data_content)
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

    # Render HTML for each section in the JSON data
    rendered_html = ""
    email_start_text = ""
    email_end_text = ""
    for section in final_data["sections"]:
        # Ensure section is a dictionary and access its keys properly
        print("Processing section:", section["position"])
        print(image_mappings.get(section["position"], ""))
        if (isinstance(section, dict) and "content" in section) and section["length"] > 0 and section["position"] not in ["email-start", "email-end"]:
            # Pass the section content into the template as "styledContent"
            
            rendered_html += template.render(styledContent=section["content"], header_image=image_mappings.get(section["position"], ""))
        elif section["position"] == "email-start" or section["position"] == "email-end":
            if section["position"] == "email-start":
                email_start_text = section["content"]
            elif section["position"] == "email-end":
                email_end_text = section["content"]
            
        else:
            print("Skipping invalid section:", section)
            


    social_html = ""

    for social in social_data:
        social_html += socials.render(
            social_link=social["social_link"],
            social_image=social["social_image"]
        )
        
    start_html = start_template.render(
        email_start=email_start_text,
        header_image="https://mcusercontent.com/a6300fadb6d053a90ae600e49/images/74b4d2c7-4ad7-82f8-8f41-b279d552422a.png"
    )
    
    start_html = start_html.replace('<p class=', '<p dir="ltr" style="color: #F2F2F2;font-family: Helvetica;font-size: 14px;font-weight: bold;text-align: center;margin: 10px 0;padding: 0;mso-line-height-rule: exactly;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%;line-height: 150%;" class=')

    end_html = end_template.render(
        email_end=email_end_text
    )
    
    end_html = end_html.replace('<p class=', '<p dir="ltr" style="color: #F2F2F2;font-family: Helvetica;font-size: 14px;font-weight: bold;text-align: center;margin: 10px 0;padding: 0;mso-line-height-rule: exactly;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%;line-height: 150%;" class=')

        
    # Output the rendered HTML
    #print(rendered_html)
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    with open(f"mps-email-{current_date}.html", "w") as output_file:

        rendered_html = rendered_html.replace('<p class=', '<p dir="ltr" style="color: #F2F2F2;font-family: Helvetica;font-size: 14px;font-weight: bold;text-align: center;margin: 10px 0;padding: 0;mso-line-height-rule: exactly;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%;line-height: 150%;" class=')
    
        output_file.write(start_html + rendered_html + end_html + social_html + end_after_social)


    print(f"HTML file generated successfully as mps-email-{current_date}.html")
    return rendered_html


if __name__ == "__main__":
    main()