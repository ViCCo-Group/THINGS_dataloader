# THINGS Dataloader command line tool

This package provides a command-line tool to download and manage [THINGS datasets](https://things-initiative.org/). 

## Installation

To install this package, use pip:

```bash
pip install git+https://github.com/ViCCo-Group/THINGS_dataloader.git
```

## Usage

`things-datasets <output_dir>` 

will show available datasets with descriptions and let's you choose the desired datasets by numbers (`Enter the numbers of the datasets you want to download (e.g., 1.1, 1.2):`). Datasets will then be downloaded to the <output_dir> in form of a zip folder called `things-datasets.zip`. 
