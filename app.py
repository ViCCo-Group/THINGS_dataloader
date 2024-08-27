import csv
import io
import zipfile
import requests
from flask import Flask, render_template, request, send_file

app = Flask(__name__)

DATASET_CSV = 'static/datasets.csv'

def load_datasets():
    datasets = {}
    with open(DATASET_CSV, mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            name = row['name']
            sub_dataset_name = row['sub-dataset name']
            description = row['description']
            download_url = row['download_url']
            if name not in datasets:
                datasets[name] = []
            datasets[name].append({
                'sub_dataset_name': sub_dataset_name,
                'description': description,
                'download_url': download_url
            })
    return datasets

@app.route('/')
def index():
    datasets = load_datasets()
    return render_template('index.html', datasets=datasets)

@app.route('/download', methods=['POST'])
def download():
    selected_urls = request.form.getlist('datasets')
    
    if not selected_urls:
        return "No datasets selected", 400

    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for url in selected_urls:
            # Extract filename from URL
            filename = url.split('/')[-1].split('?')[0]
            # Download file and add to zip
            response = requests.get(url)
            zip_file.writestr(filename, response.content)

    zip_buffer.seek(0)
    return send_file(zip_buffer, as_attachment=True, download_name='datasets.zip', mimetype='application/zip')

if __name__ == '__main__':
    app.run(debug=True)