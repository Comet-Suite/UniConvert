from setuptools import setup, find_packages
from pathlib import Path

setup(
    name="uniconvert",
    version="0.1.0",
    description="Universal multi-format file converter",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author="UniConvert Contributors",
    license="MIT",
    packages=find_packages(exclude=("tests", "installers")),
    include_package_data=True,
    package_data={"uniconvert": ["../assets/*"]},
    install_requires=[
        "PyQt6>=6.5",
        "Pillow>=10.0",
    ],
    extras_require={
        "full": ["pandas", "openpyxl", "pypdf", "PyYAML"],
    },
    entry_points={
        "console_scripts": ["uniconvert=uniconvert.gui:run"],
        "gui_scripts": ["uniconvert-gui=uniconvert.gui:run"],
    },
    python_requires=">=3.9",
)
