"""Setup script for pip installation"""
from setuptools import setup, find_packages

setup(
    name="stoat",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "typer[all]>=0.12.0",
        "rich>=13.7.0",
        "pydantic>=2.5.0",
        "httpx>=0.27.0",
        "psutil>=5.9.0",
        "rapidfuzz>=3.6.0",
        "structlog>=24.1.0",
        "python-dotenv>=1.0.0",
        "toml>=0.10.2",
    ],
    entry_points={
        "console_scripts": [
            "stoat=stoat.cli:app",
        ],
    },
)
