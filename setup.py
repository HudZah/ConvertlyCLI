from setuptools import setup, find_packages

setup(
    name="convertly",
    version="0.4.7",
    packages=find_packages(),
    entry_points={"console_scripts": ["conv=file_converter.convertly:main"]},
    install_requires=["requests"],
    python_requires=">=3.6",
    author="HudZah",
    author_email="hudzah@hudzah.com",
    description="A tool to convert and manipulate media files",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/HudZah/Convertly",
    license="MIT",
)
