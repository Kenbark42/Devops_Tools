#!/usr/bin/env python
"""
DevOps Toolkit - A comprehensive Python-based toolkit for DevOps workflows.
"""
from setuptools import setup, find_packages
import os
import re

# Read version from __init__.py
with open(os.path.join("src", "devops_toolkit", "__init__.py"), "r") as f:
    version_match = re.search(r'__version__ = ["\']([^"\']*)["\']', f.read())
    version = version_match.group(1) if version_match else "0.1.0"

# Read long description from README
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# Define requirements
requirements = [
    "click>=8.0.0",
    "pyyaml>=6.0",
    "pydantic>=2.0.0",
    "rich>=12.0.0",
]

# Optional dependencies
extras_require = {
    "aws": [
        "boto3>=1.26.0",
        "botocore>=1.29.0",
    ],
    "kubernetes": [
        "kubernetes>=24.2.0",
    ],
    "monitoring": [
        "prometheus-client>=0.16.0",
        "requests>=2.28.0",
    ],
    "dev": [
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "black>=23.0.0",
        "flake8>=6.0.0",
        "mypy>=1.0.0",
        "isort>=5.10.0",
        "build>=0.10.0",
        "twine>=4.0.0",
    ],
}

# Add an 'all' extra that includes everything except 'dev'
extras_require["all"] = [
    req for extra, reqs in extras_require.items()
    for req in reqs if extra != "dev"
]

setup(
    name="devops-toolkit",
    version=version,
    description="A comprehensive Python-based toolkit for DevOps workflows",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Kenbark42",
    author_email="kenbark42@example.com",
    url="https://github.com/kenbark42/devops-toolkit",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require=extras_require,
    entry_points={
        "console_scripts": [
            "devops=devops_toolkit.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Build Tools",
        "Topic :: System :: Installation/Setup",
        "Topic :: System :: Systems Administration",
    ],
)
