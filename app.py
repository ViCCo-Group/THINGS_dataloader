from flask import Flask, render_template, request, jsonify
import csv

app = Flask(__name__)

DATASET_CSV = 'static/datasets.csv'

def load_datasets():
    datasets = []
    with open(DATASET_CSV, mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            row['download_urls'] = row['download_urls'].split(',')
            datasets.append(row)
    return datasets

@app.route('/')
def index():
    datasets = load_datasets()
    return render_template('index.html', datasets=datasets)

@app.route('/download', methods=['POST'])
def download():
    selected_datasets = request.form.getlist('datasets')
    
    if not selected_datasets:
        return "No dataset selected.", 400
    
    datasets = load_datasets()
    download_links = []
    
    for dataset in datasets:
        if dataset['name'] in selected_datasets:
            download_links.extend(dataset['download_urls'])
    
    # Return the list of download links as a JSON response
    return jsonify(download_links)

if __name__ == '__main__':
    app.run(debug=True)
