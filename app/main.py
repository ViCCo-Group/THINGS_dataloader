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
    with open('static/datasets.csv', mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            name = row['name']
            sub_dataset_name = row['sub-dataset name']
            description = row['description']
            files = row['files'].split(',')
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
    with open('static/dataset_descriptions.csv', mode='r') as file:
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
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for foldername, subfolders, filenames in os.walk(source_dir):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)

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
            # Identify the dataset entry corresponding to the URL
            dataset_info = next(
                (item for items in datasets.values() for item in items if item['download_url'] == url), 
                None
            )
            
            if not dataset_info:
                continue
            
            folder_name = dataset_info['folder_name']
            zip_path = os.path.join(download_dir, folder_name + '.zip')

            try:
                # Download the zip file
                response = requests.get(url, stream=True)
                response.raise_for_status()

                with open(zip_path, 'wb') as zip_file:
                    zip_file.write(response.content)

                # Extract and rename the zip file
                extract_and_rename_zip(zip_path, extracted_dir, folder_name)
                extracted_folders.append(os.path.join(extracted_dir, folder_name))
                
            except requests.RequestException as e:
                return f"Error downloading file: {e}", 500
            except zipfile.BadZipFile as e:
                return f"Error processing zip file: {e}", 500

        main_zip_path = os.path.join(temp_dir, 'things-datasets.zip')
        zip_all_folders(extracted_dir, main_zip_path)

        return send_file(main_zip_path, as_attachment=True, download_name='things-datasets.zip', mimetype='application/zip')

if __name__ == '__main__':
    app.run(debug=True)
