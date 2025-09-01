import csv


def parse_csv(input_file, output_file):

    with open(input_file, newline='', encoding='utf-8') as csvfile_in, \
        open(output_file, 'w', newline='', encoding='utf-8') as csvfile_out:
        reader = csv.DictReader(csvfile_in)
        writer = csv.writer(csvfile_out)
        writer.writerow(['email', 'name'])
        for row in reader:
            email = row.get('Contact Email', '').strip()
            name = row.get('First Name', '').strip()
            if not email or email == '(not allowed)':
                continue
            writer.writerow([email, name]) 
            
if __name__ == '__main__':
    input_file = 'Media Production Export All Members 2025-07-14 2217.csv'
    output_file = 'emails_extracted.csv'
    
    parse_csv(input_file, output_file)
    print(f"Extracted emails saved to {output_file}")