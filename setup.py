"""Setup configuration for Brand Metadata Generator."""

from setuptools import setup, find_packages

setup(
    name="brand-metadata-generator",
    version="0.1.0",
    description="Multi-agent system for generating retail brand classification metadata",
    author="Your Team",
    author_email="your-email@example.com",
    packages=find_packages(exclude=["tests*", "docs*"]),
    python_requires=">=3.9",
    install_requires=[
        "boto3>=1.34.0",
        "strands-agents>=0.1.0",
        "pandas>=2.0.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
