import csv
import zipfile
import shutil
import tempfile
import os
import subprocess
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
            include_files = row['include_files'].split('; ')

            if name not in datasets:
                datasets[name] = []

            datasets[name].append({
                'sub_dataset_name': sub_dataset_name,
                'description': description,
                'files': files,
                'download_url': download_url,
                'size': size,
                'folder_name': f"{name}_{sub_dataset_name.replace(' ', '_')}",
                'include_files': include_files
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

def extract_and_rename_zip(zip_path, extract_to, new_folder_name):
    try:
        temp_extract_to = os.path.join(extract_to, 'temp_extract')
        os.makedirs(temp_extract_to, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_to)

        top_level_dir = os.listdir(temp_extract_to)[0]
        original_top_level_dir = os.path.join(temp_extract_to, top_level_dir)
        new_path = os.path.join(extract_to, new_folder_name)
        
        shutil.move(original_top_level_dir, new_path)
        shutil.rmtree(temp_extract_to)

    except zipfile.BadZipFile as e:
        print(f"Error extracting {zip_path}: {e}")
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def zip_all_folders(source_dir, output_zip):
    try:
        if not os.path.exists(source_dir) or not os.listdir(source_dir):
            raise Exception("Source directory does not exist or is empty.")

        print(f"Zipping contents of {source_dir} into {output_zip}")  # Debug print

        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for foldername, subfolders, filenames in os.walk(source_dir):
                print(f"Processing folder: {foldername}")  # Debug: Show folder being processed
                for filename in filenames:
                    file_path = os.path.join(foldername, filename)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
                    print(f"Added file: {file_path}")  # Debug: Show each file added

        print(f"Successfully created {output_zip}. Size: {os.path.getsize(output_zip)} bytes")

    except Exception as e:
        print(f"Error creating zip file: {e}")
        raise

def download_file(url, output_path):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(output_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
    except requests.RequestException as e:
        print(f"Error downloading file from {url}: {e}")
        raise

def get_filename_from_response(response):
    content_disposition = response.headers.get('Content-Disposition')
    if content_disposition:
        parts = content_disposition.split(';')
        for part in parts:
            if 'filename=' in part:
                filename = part.split('=')[-1].strip('"')
                return filename
    return None

def download_dataset_openneuro(dataset_id, include_files, download_path):
    try:
        # Ensure the target directory exists
        os.makedirs(download_path, exist_ok=True)
        
        # Construct the openneuro-py command
        command = ['openneuro-py', 'download', f'--dataset={dataset_id}', f'--target-dir={download_path}']
        
        # Add include files if specified
        if include_files:
            for include_file in include_files:
                command.append(f'--include={include_file}')
        
        print(f"Running command: {' '.join(command)}")  # Debug: Print the command
        
        # Run the command
        result = subprocess.run(command, capture_output=True, text=True)
        
        # Check if the download command was successful
        if result.returncode != 0:
            print(f"Error downloading dataset {dataset_id}: {result.stderr}")
            raise Exception(f"Download failed: {result.stderr}")

        # Check if the directory is empty
        if not os.listdir(download_path):
            raise Exception("Download directory is empty. No files were downloaded.")
        
        print(f"Successfully downloaded dataset {dataset_id} to {download_path}")
    
    except Exception as e:
        print(f"Error during download: {e}")
        raise

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
            include_files = dataset_info.get('include_files')


            if 'figshare' in url:
                zip_path = os.path.join(download_dir, folder_name + '.zip')
                
                try:
                    # Download the zip file
                    download_file(url, zip_path)

                    # Extract and rename the zip file
                    extract_and_rename_zip(zip_path, extracted_dir, folder_name)
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
                    extracted_folders.append(folder_path)
                
                except requests.RequestException as e:
                    return f"Error downloading file: {e}", 500

            elif 'openneuro' in url:                            
                dataset_id = url.split('/')[-1]
                #target_dir = os.path.join(download_dir, folder_name)
                try:
                    # Download the dataset
                    download_dataset_openneuro(dataset_id, include_files, extracted_dir)
                    
                    # Append the target_dir to extracted_folders
                    extracted_folders.append(extracted_dir)
                except Exception as e:
                    return f"Error executing openneuro-py command: {e}", 500

        main_zip_path = os.path.join(temp_dir, 'things-datasets.zip')
        if extracted_folders:
            zip_all_folders(extracted_dir, main_zip_path)
        else:
            # If no folders were extracted, create an empty zip file
            with zipfile.ZipFile(main_zip_path, 'w') as zipf:
                pass

        if not os.path.exists(main_zip_path) or os.path.getsize(main_zip_path) == 0:
            return "Failed to create the zip file", 500

        return send_file(main_zip_path, as_attachment=True, download_name='things-datasets.zip', mimetype='application/zip')

if __name__ == '__main__':
    app.run(debug=True)
