from setuptools import setup, find_packages

setup(
    name="your_package",
    version="0.1.0",
    packages=find_packages(),
    entry_points={"console_scripts": ["conv=file_converter.convert:main"]},
    install_requires=[
        "openai",
    ],
    python_requires=">=3.6",
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool to convert and manipulate media files",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/your_package",
    license="MIT",
)
