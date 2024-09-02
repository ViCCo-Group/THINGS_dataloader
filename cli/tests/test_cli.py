import subprocess
import tempfile
import os

def test_main():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a dummy CSV file
        csv_path = os.path.join(temp_dir, 'datasets.csv')
        with open(csv_path, 'w') as f:
            f.write('name,sub-dataset name,description,download_url\n')
            f.write('Dataset1,SubDataset1,Description,http://example.com/file.zip\n')

        # Run the command-line tool
        result = subprocess.run(['things-datasets', csv_path, temp_dir], capture_output=True, text=True)

        assert result.returncode == 0
        assert 'All selected datasets are packaged into' in result.stdout
