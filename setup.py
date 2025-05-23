from setuptools import setup, find_packages

setup(
    name="ps1db",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click",
        "sqlalchemy",
        "tabulate"
    ],
    entry_points={
        'console_scripts': [
            'ps1db=ps1db:main',
        ],
    },
    author="Nicholas Flynn",
    description="A PlayStation 1 game collection manager",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/UnknownUserdot/PS1.db",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
) 