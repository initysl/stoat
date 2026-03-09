"""Pytest configuration and fixtures"""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def sample_files(temp_dir):
    """Create sample files for testing"""
    files = {
        "test.txt": "Sample text file",
        "document.pdf": b"PDF content",
        "image.png": b"PNG content",
    }

    for filename, content in files.items():
        filepath = temp_dir / filename
        if isinstance(content, str):
            filepath.write_text(content)
        else:
            filepath.write_bytes(content)

    return temp_dir
