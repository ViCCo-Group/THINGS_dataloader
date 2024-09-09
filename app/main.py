import csv
import zipfile
import shutil
import tempfile
import os
import requests
from flask import Flask, render_template, request, send_file

app = Flask(__name__)

def load_datasets():
    datasets = {}
    with open('app/static/datasets.csv', mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            name = row['name']
            sub_dataset_name = row['sub-dataset name']
            description = row['description']
            files = row['files'].split('; ')
            download_url = row['download_url']
            size = row['size']
            
            if name not in datasets:
                datasets[name] = []

            datasets[name].append({
                'sub_dataset_name': sub_dataset_name,
                'description': description,
                'files': files,
                'download_url': download_url,
                'size': size,
                'folder_name': f"{name}_{sub_dataset_name.replace(' ', '_')}"
            })
    return datasets

def load_descriptions():
    descriptions = {}
    with open('app/static/dataset_descriptions.csv', mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            name = row['name']
            name_description = row['name_description']
            descriptions[name] = name_description
    return descriptions

def extract_zip(zip_path, extract_to):
    """Extracts a zip file and handles nested zips if any."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)

        # Check for nested zip files and extract them as well
        for root, _, files in os.walk(extract_to):
            for file in files:
                if file.endswith('.zip'):
                    nested_zip_path = os.path.join(root, file)
                    nested_extract_to = os.path.join(root, file[:-4])  # Removing .zip from the folder name
                    os.makedirs(nested_extract_to, exist_ok=True)
                    extract_zip(nested_zip_path, nested_extract_to)
                    os.remove(nested_zip_path)  # Optionally remove the nested zip file after extraction

    except zipfile.BadZipFile as e:
        print(f"Error extracting {zip_path}: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def zip_all_folders(source_dir, output_zip):
    try:
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for foldername, subfolders, filenames in os.walk(source_dir):
                for filename in filenames:
                    file_path = os.path.join(foldername, filename)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
        print(f"Successfully created {output_zip}.")
    except Exception as e:
        print(f"Error creating zip file: {e}")

def download_file(url, output_path):
    """Download a file from a URL and save it to the specified path."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raises HTTPError for bad responses
        with open(output_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
    except requests.RequestException as e:
        print(f"Error downloading file from {url}: {e}")
        raise

def get_filename_from_response(response):
    """Extract filename from the Content-Disposition header if available."""
    content_disposition = response.headers.get('Content-Disposition')
    if content_disposition:
        parts = content_disposition.split(';')
        for part in parts:
            if 'filename=' in part:
                filename = part.split('=')[-1].strip('"')
                return filename
    return None

@app.route('/')
def index():
    datasets = load_datasets()
    descriptions = load_descriptions()
    return render_template('index.html', datasets=datasets, descriptions=descriptions)

@app.route('/download', methods=['POST'])
def download():
    selected_urls = request.form.getlist('datasets')
    
    if not selected_urls:
        return "No datasets selected", 400

    datasets = load_datasets()

    with tempfile.TemporaryDirectory() as temp_dir:
        download_dir = os.path.join(temp_dir, 'downloads')
        extracted_dir = os.path.join(temp_dir, 'extracted')
        os.makedirs(download_dir, exist_ok=True)
        os.makedirs(extracted_dir, exist_ok=True)

        extracted_folders = []

        for url in selected_urls:
            dataset_info = next(
                (item for items in datasets.values() for item in items if item['download_url'] == url), 
                None
            )
            
            if not dataset_info:
                continue
            
            folder_name = dataset_info['folder_name']
            files = dataset_info['files']

            if 'figshare' in url:
                zip_path = os.path.join(download_dir, folder_name + '.zip')
                
                try:
                    # Download the zip file
                    download_file(url, zip_path)

                    # Extract and rename the zip file
                    extract_zip(zip_path, os.path.join(extracted_dir, folder_name))
                    extracted_folders.append(os.path.join(extracted_dir, folder_name))
                    
                except requests.RequestException as e:
                    return f"Error downloading file: {e}", 500
                except zipfile.BadZipFile as e:
                    return f"Error processing zip file: {e}", 500
            
            elif 'osf' in url:
                folder_path = os.path.join(extracted_dir, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                
                try:
                    # Download the file from OSF and get the original filename
                    response = requests.get(url, stream=True)
                    response.raise_for_status()

                    filename = get_filename_from_response(response)
                    if filename is None:
                        filename = url.split('/')[-1]  # Use the last part of URL as fallback
                    
                    file_path = os.path.join(folder_path, filename)
                    download_file(url, file_path)

                    # Check if the downloaded file is a zip and extract if true
                    if file_path.endswith('.zip'):
                        extract_zip(file_path, folder_path)
                        os.remove(file_path)  # Optionally remove the zip file after extraction
                    
                    extracted_folders.append(folder_path)
                
                except requests.RequestException as e:
                    return f"Error downloading file: {e}", 500

        main_zip_path = os.path.join(temp_dir, 'things-datasets.zip')
        zip_all_folders(extracted_dir, main_zip_path)

        if not os.path.exists(main_zip_path) or os.path.getsize(main_zip_path) == 0:
            return "Failed to create the zip file", 500

        return send_file(main_zip_path, as_attachment=True, download_name='things-datasets.zip', mimetype='application/zip')

if __name__ == '__main__':
    app.run(debug=True)
