import csv
import zipfile
import shutil
import tempfile
import os
import subprocess
import requests
from flask import Flask, render_template, request, send_file

app = Flask(__name__)

def extract_derivative_attr(str):
    str = str.strip()
    l = str.split('; ')
    if len(l) == 0 or (len(l) == 1 and l[0] == ""):
        return None
    else:
        return l 

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
            value_html = name+"_"+sub_dataset_name
            size = row['size']
            exclude_files = extract_derivative_attr(row['exclude_files'])#.split('; ')
            include_files = extract_derivative_attr(row['include_files'])#.split('; ')
            code = row.get('code', '')  # Fetch the code, if present

            if name not in datasets:
                datasets[name] = []

            datasets[name].append({
                'sub_dataset_name': sub_dataset_name,
                'description': description,
                'files': files,
                'download_url': download_url,
                'value_html': value_html,
                'size': size,
                'folder_name': f"{name}_{sub_dataset_name.replace(' ', '_')}",
                'exclude_files': exclude_files,
                'include_files': include_files,
                'code': code
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


def download_dataset_openneuro(dataset_id, include_files, exclude_files, download_path):
    try:
        # Ensure the target directory exists
        os.makedirs(download_path, exist_ok=True)
        
        # Construct the base openneuro-py command
        command = ['openneuro-py', 'download', f'--dataset={dataset_id}', f'--target-dir={download_path}']

        # Determine which flag to use based on which list is not empty


        if exclude_files is not None:
            command.extend([f'--exclude={",".join(exclude_files)}'])
        elif include_files:
            command.extend([f'--include={",".join(include_files)}'])
        
        print(f"Running command: {' '.join(command)}")  # Debug: Print the constructed command
        
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


def create_readme(selected_urls, datasets, descriptions, readme_path):
    with open(readme_path, 'w') as readme:
        for name, items in datasets.items():
            for item in items:
                # Check if the dataset's download URL is in the selected URLs
                if item['download_url'] in selected_urls:
                    name_description = descriptions.get(name, 'No description available')
                    readme.write(f"Name: {name}\n")
                    readme.write(f"Name Description: {name_description}\n")
                    readme.write(f"Sub-dataset Name: {item['sub_dataset_name']}\n")
                    readme.write(f"Description: {item['description']}\n")
                    readme.write(f"Files: {', '.join(item['files'])}\n")
                    readme.write(f"Download URL: {item['download_url']}\n")
                    readme.write(f"Size: {item['size']}\n")
                    readme.write(f"Code: {item['code']}\n")
                    readme.write("\n---\n\n")

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
    descriptions = load_descriptions()

    with tempfile.TemporaryDirectory() as temp_dir:
        download_dir = os.path.join(temp_dir, 'downloads')
        extracted_dir = os.path.join(temp_dir, 'extracted')
        os.makedirs(download_dir, exist_ok=True)
        os.makedirs(extracted_dir, exist_ok=True)

        extracted_folders = []

        for url in selected_urls:
            dataset_info = next(
                (item for items in datasets.values() for item in items if item['value_html'] == url), 
                None
            )

            if not dataset_info:
                continue

            url_value = dataset_info['download_url']
            folder_name = dataset_info['folder_name']
            files = dataset_info['files']
            exclude_files = dataset_info.get('exclude_files')
            include_files = dataset_info.get('include_files')

            if 'figshare' in url_value:
                zip_path = os.path.join(download_dir, folder_name + '.zip')
                
                try:
                    # Download the zip file
                    download_file(url_value, zip_path)

                    # Extract and rename the zip file
                    extract_and_rename_zip(zip_path, extracted_dir, folder_name)
                    extracted_folders.append(os.path.join(extracted_dir, folder_name))
                    
                except requests.RequestException as e:
                    return f"Error downloading file: {e}", 500
                except zipfile.BadZipFile as e:
                    return f"Error processing zip file: {e}", 500
            
            elif 'osf' in url_value:
                folder_path = os.path.join(extracted_dir, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                
                try:
                    # Download the file from OSF and get the original filename
                    response = requests.get(url_value, stream=True)
                    response.raise_for_status()

                    filename = get_filename_from_response(response)
                    if filename is None:
                        filename = url_value.split('/')[-1]  # Use the last part of URL as fallback
                    
                    file_path = os.path.join(folder_path, filename)
                    download_file(url_value, file_path)
                    extracted_folders.append(folder_path)
                
                except requests.RequestException as e:
                    return f"Error downloading file: {e}", 500

            elif 'openneuro' in url_value:                            
                dataset_id = url_value.split('/')[-1]
                target_folder = os.path.join(extracted_dir, folder_name)

                try:
                    # Ensure the target folder exists
                    os.makedirs(target_folder, exist_ok=True)

                    # Pass include_files and exclude_files to the function
                    download_dataset_openneuro(dataset_id, include_files, exclude_files, target_folder)

                    # Append the target_folder to extracted_folders
                    extracted_folders.append(target_folder)

                except Exception as e:
                    return f"Error executing openneuro-py command: {e}", 500

        readme_path = os.path.join(extracted_dir, 'README.txt')
        create_readme(selected_urls, datasets, descriptions, readme_path)  # Create the README file with only selected datasets

        main_zip_path = os.path.join(temp_dir, 'things-datasets.zip')
        if extracted_folders:
            zip_all_folders(extracted_dir, main_zip_path)
        else:
            with zipfile.ZipFile(main_zip_path, 'w') as zipf:
                pass

        if not os.path.exists(main_zip_path) or os.path.getsize(main_zip_path) == 0:
            return "Failed to create the zip file", 500

        return send_file(main_zip_path, as_attachment=True, download_name='things-datasets.zip', mimetype='application/zip')

if __name__ == '__main__':
    app.run(debug=True)
