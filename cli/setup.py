from setuptools import setup, find_packages

setup(
    name='things_datasets',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'pandas>=1.0.0'
    ],
    entry_points={
        'console_scripts': [
            'things-datasets=things_datasets.cli:main',
        ],
    },
    include_package_data=True,
    description='Download and manage THINGS datasets.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Julia-Katharina Pfarr',
    author_email='juliakatharina.pfarr@gmail.com',
    url='https://github.com/ViCCo-Group/THINGS_dataloader',
)
