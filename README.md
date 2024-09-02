# Data Loader for THINGS data

This repo is under active development and will let you query and load data from the [THINGS initiative](https://things-initiative.org/). tbc

## Install via pip and run via command line

```bash
pip install git+https://github.com/ViCCo-Group/THINGS_dataloader.git
``` 

### Usage

`things-datasets <output_dir>` 

will show available datasets with descriptions and let's you choose the desired datasets by numbers (`Enter the numbers of the datasets you want to download (e.g., 1.1, 1.2):`). Datasets will then be downloaded to the <output_dir> in form of a zip folder called `things-datasets.zip`. 

## Run dataloader as a web interface locally

`pip install flask`<br>
`git clone git@github.com:ViCCo-Group/THINGS_dataloader.git`<br>
`cd THINGS_dataloader`<br>
`python website/app.py`



