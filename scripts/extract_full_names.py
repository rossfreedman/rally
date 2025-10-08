#!/usr/bin/env python3
"""
Extract complete first and last names from HTML files by parsing the JavaScript template structure.
This will find both UserFName and UserLName fields and combine them properly.
"""

import re
import csv
import os
import glob
from bs4 import BeautifulSoup

def extract_full_names(csv_file_path, html_directory):
    """
    Extract complete first and last names from HTML files by parsing the JavaScript template.
    """
    
    print(f"Processing HTML files in: {html_directory}")
    
    # Find all HTML files
    html_files = glob.glob(os.path.join(html_directory, "*.html"))
    html_files.sort()
    
    print(f"Found {len(html_files)} HTML files to process")
    
    # Build comprehensive contact list
    all_contacts = []
    
    for html_file in html_files:
        print(f"Processing {os.path.basename(html_file)}...")
        
        try:
            with open(html_file, 'r', encoding='utf-8') as file:
                content = file.read()
        except Exception as e:
            print(f"Error reading {html_file}: {e}")
            continue
        
        # Look for the JavaScript template line that contains the data
        lines = content.split('\n')
        data_line = None
        
        for line in lines:
            if 'items.push' in line and 'UserFName' in line and 'UserLName' in line and 'EmailAddy' in line:
                data_line = line
                break
        
        if not data_line:
            print(f"  No template data found in {os.path.basename(html_file)}")
            continue
        
        # Extract all the data arrays from the line
        # Look for patterns like: item.UserFName, item.UserLName, item.EmailAddy, etc.
        
        # Find all the data arrays in the file
        data_arrays = extract_data_arrays(content)
        
        if not data_arrays:
            print(f"  No data arrays found in {os.path.basename(html_file)}")
            continue
        
        # Process each data array
        for data_array in data_arrays:
            contacts_from_array = extract_contacts_from_array(data_array)
            all_contacts.extend(contacts_from_array)
        
        print(f"  Found {len([c for c in all_contacts if any(c['email'] in str(data_array) for data_array in data_arrays)])} contacts")
    
    print(f"\nExtracted {len(all_contacts)} contacts total")
    
    # Remove duplicates based on email
    unique_contacts = []
    seen_emails = set()
    
    for contact in all_contacts:
        email_lower = contact['email'].lower()
        if email_lower not in seen_emails:
            unique_contacts.append(contact)
            seen_emails.add(email_lower)
    
    print(f"Removed duplicates, {len(unique_contacts)} unique contacts")
    
    # Sort contacts by name
    unique_contacts.sort(key=lambda x: x['name'])
    
    # Write new CSV
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'email', 'phone', 'cell_phone']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for contact in unique_contacts:
            writer.writerow(contact)
    
    print(f"Updated CSV file: {csv_file_path}")
    
    # Count contacts with phone numbers
    contacts_with_phones = sum(1 for c in unique_contacts if c.get('phone', ''))
    print(f"Contacts with phone numbers: {contacts_with_phones}")
    
    # Show preview of contacts
    print("\nPreview of contacts:")
    count = 0
    for contact in unique_contacts:
        print(f"{count+1}. {contact['name']} - {contact['email']} - {contact['phone']}")
        count += 1
        if count >= 20:
            break

def extract_data_arrays(content):
    """Extract data arrays from the HTML content."""
    
    data_arrays = []
    
    # Look for JavaScript arrays containing contact data
    # Pattern: var data = [{...}, {...}, ...];
    array_patterns = [
        r'var\s+data\s*=\s*\[(.*?)\];',
        r'data\s*=\s*\[(.*?)\];',
        r'items\s*=\s*\[(.*?)\];',
        r'var\s+items\s*=\s*\[(.*?)\];'
    ]
    
    for pattern in array_patterns:
        matches = re.findall(pattern, content, re.DOTALL)
        for match in matches:
            # Try to parse the array content
            try:
                # This is a simplified approach - we'll look for individual objects
                objects = extract_objects_from_array_string(match)
                data_arrays.extend(objects)
            except Exception as e:
                print(f"Error parsing array: {e}")
                continue
    
    # Also look for inline data in the template
    # Look for patterns like: {UserFName: "John", UserLName: "Smith", EmailAddy: "john@email.com"}
    inline_pattern = r'\{[^}]*UserFName[^}]*UserLName[^}]*EmailAddy[^}]*\}'
    inline_matches = re.findall(inline_pattern, content, re.DOTALL)
    
    for match in inline_matches:
        try:
            obj = parse_inline_object(match)
            if obj:
                data_arrays.append(obj)
        except Exception as e:
            continue
    
    return data_arrays

def extract_objects_from_array_string(array_string):
    """Extract individual objects from an array string."""
    
    objects = []
    
    # Look for object patterns in the array string
    # This is a simplified approach - we'll look for key-value pairs
    obj_pattern = r'\{[^}]*\}'
    obj_matches = re.findall(obj_pattern, array_string)
    
    for obj_match in obj_matches:
        try:
            obj = parse_object_string(obj_match)
            if obj:
                objects.append(obj)
        except Exception as e:
            continue
    
    return objects

def parse_object_string(obj_string):
    """Parse an object string to extract key-value pairs."""
    
    obj = {}
    
    # Extract key-value pairs
    # Pattern: key: "value" or key: value
    kv_pattern = r'(\w+)\s*:\s*["\']([^"\']*)["\']'
    matches = re.findall(kv_pattern, obj_string)
    
    for key, value in matches:
        obj[key] = value
    
    return obj if obj else None

def parse_inline_object(obj_string):
    """Parse an inline object string."""
    
    obj = {}
    
    # Extract key-value pairs
    kv_pattern = r'(\w+)\s*:\s*["\']([^"\']*)["\']'
    matches = re.findall(kv_pattern, obj_string)
    
    for key, value in matches:
        obj[key] = value
    
    return obj if obj else None

def extract_contacts_from_array(data_array):
    """Extract contacts from a data array."""
    
    contacts = []
    
    if not isinstance(data_array, dict):
        return contacts
    
    # Extract the contact information
    first_name = data_array.get('UserFName', '').strip()
    last_name = data_array.get('UserLName', '').strip()
    email = data_array.get('EmailAddy', '').strip()
    phone = data_array.get('Phone', '').strip()
    cell_phone = data_array.get('CellPhone', '').strip()
    
    if not email:
        return contacts
    
    # Combine first and last name
    if first_name and last_name:
        full_name = f"{first_name} {last_name}"
    elif last_name:
        full_name = last_name
    elif first_name:
        full_name = first_name
    else:
        full_name = "Unknown"
    
    # Format phone number
    formatted_phone = format_phone_number(phone) if phone else ''
    formatted_cell = format_phone_number(cell_phone) if cell_phone else ''
    
    contact = {
        'name': full_name,
        'email': email,
        'phone': formatted_phone,
        'cell_phone': formatted_cell
    }
    
    contacts.append(contact)
    
    return contacts

def format_phone_number(phone):
    """Format phone number to standard format."""
    
    if not phone:
        return ''
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Format as (XXX) XXX-XXXX
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    
    return phone

if __name__ == "__main__":
    csv_file = "/Users/rossfreedman/dev/rally/data/apta_directory.csv"
    html_directory = "/Users/rossfreedman/dev/rally/data/APTA_Contact _Info"
    
    extract_full_names(csv_file, html_directory)
