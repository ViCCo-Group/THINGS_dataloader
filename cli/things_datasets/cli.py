import csv
import os
import subprocess
import zipfile
import shutil
import pandas as pd
from pathlib import Path
import argparse

# Define the path to the CSV file
CSV_FILE_PATH = 'static/datasets.csv'

def load_datasets():
    datasets = {}
    try:
        with open(CSV_FILE_PATH, mode='r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                name = row['name']
                sub_dataset_name = row['sub-dataset name']
                description = row['description']
                size = row.get('size', 'Unknown')  # Size if available, else 'Unknown'
                download_url = row['download_url']

                if name not in datasets:
                    datasets[name] = {
                        'description': '',
                        'sub_datasets': []
                    }
                
                datasets[name]['sub_datasets'].append({
                    'sub_dataset_name': sub_dataset_name,
                    'description': description,
                    'size': size,
                    'download_url': download_url
                })
        return datasets
    except FileNotFoundError:
        print(f"Error: {CSV_FILE_PATH} not found.")
        exit(1)

def list_datasets(datasets):
    print("Available Datasets:\n")
    for idx, (name, info) in enumerate(datasets.items(), start=1):
        print(f"{idx}. {name}")
        print(f"   Description: {info['description']}")
        for sub_idx, sub in enumerate(info['sub_datasets'], start=1):
            print(f"      {idx}.{sub_idx}. {sub['sub_dataset_name']}")
            print(f"         Size: {sub['size']}")
            print(f"         Description: {sub['description']}")
    print()

def download_file(url, output_filename):
    try:
        command = ['wget', '-O', output_filename, url]
        subprocess.run(command, check=True)
        print(f"Downloaded {output_filename} successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error downloading {url}: {e}")

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

        print(f"Successfully extracted {zip_path} and renamed the top-level directory to {new_folder_name}.")
    except zipfile.BadZipFile as e:
        print(f"Error extracting {zip_path}: {e}")
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def process_datasets(output_dir):
    df = pd.read_csv(CSV_FILE_PATH)
    
    for _, row in df.iterrows():
        zip_url = row['download_url']
        new_folder_name = f"{row['name']}_{row['sub-dataset name']}"
        zip_filename = zip_url.split('/')[-1]
        zip_path = os.path.join(output_dir, zip_filename)
        
        download_file(zip_url, zip_path)
        extract_and_rename_zip(zip_path, output_dir, new_folder_name)

def zip_all_folders(source_dir, output_zip):
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for foldername, subfolders, filenames in os.walk(source_dir):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)
    
    print(f"Successfully created {output_zip}.")

def main():
    parser = argparse.ArgumentParser(description='Download and package THINGS datasets.')
    parser.add_argument('output_dir', type=str, help='Directory to store the final zip folder and temporary files.')
    args = parser.parse_args()

    output_dir = args.output_dir
    datasets = load_datasets()
    list_datasets(datasets)

    selection = input("Enter the numbers of the datasets you want to download (e.g., 1.1, 1.2): ").split(',')

    selected_urls = []
    folder_names = []
    for sel in selection:
        try:
            main_idx, sub_idx = map(int, sel.split('.'))
            main_key = list(datasets.keys())[main_idx - 1]
            sub_dataset = datasets[main_key]['sub_datasets'][sub_idx - 1]
            selected_urls.append((sub_dataset['download_url'], sub_dataset['sub_dataset_name']))
            folder_name = f"{main_key}_{sub_dataset['sub_dataset_name'].replace(' ', '_')}"
            folder_names.append(folder_name)
        except (ValueError, IndexError):
            print(f"Invalid selection: {sel}. Skipping.")

    if not selected_urls:
        print("No valid datasets selected. Exiting.")
        return

    download_dir = os.path.join(output_dir, 'downloads')
    extracted_dir = os.path.join(output_dir, 'extracted')
    os.makedirs(download_dir, exist_ok=True)
    os.makedirs(extracted_dir, exist_ok=True)

    extracted_folders = []

    for (url, sub_dataset_name), folder_name in zip(selected_urls, folder_names):
        filename = folder_name + '.zip'
        output_path = os.path.join(download_dir, filename)
        print(f"Downloading {filename} from {url}...")
        download_file(url, output_path)

        print(f"Extracting {output_path}...")
        extract_and_rename_zip(output_path, extracted_dir, folder_name)

        extracted_folders.append(os.path.join(extracted_dir, folder_name))

    main_zip_path = os.path.join(output_dir, 'things-datasets.zip')
    zip_all_folders(extracted_dir, main_zip_path)

    shutil.rmtree(download_dir)
    shutil.rmtree(extracted_dir)

    print(f"All selected datasets are packaged into {main_zip_path}.")
