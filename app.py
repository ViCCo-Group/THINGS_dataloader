import csv
import io
import zipfile
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
                'size': size
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

    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for url in selected_urls:
            try:
                # Download the zip file from the URL
                response = requests.get(url)
                response.raise_for_status()
                
                # Read the downloaded zip file
                with io.BytesIO(response.content) as temp_zip:
                    with zipfile.ZipFile(temp_zip) as temp_zip_file:
                        # Extract all files from the temporary zip
                        for file_info in temp_zip_file.infolist():
                            with temp_zip_file.open(file_info) as file:
                                # Add each file to the final zip archive
                                zip_file.writestr(file_info, file.read())
            except requests.RequestException as e:
                return f"Error downloading file: {e}", 500
            except zipfile.BadZipFile as e:
                return f"Error processing zip file: {e}", 500

    zip_buffer.seek(0)
    return send_file(zip_buffer, as_attachment=True, download_name='datasets.zip', mimetype='application/zip')

if __name__ == '__main__':
    app.run(debug=True)
