# -*- coding: utf-8 -*-

from distutils.core import setup

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="apertium2ud",
    packages=setuptools.find_packages(),
    version="0.0.1",
    description="Converting universal tags to Apertium tags.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Anton Alekseev",
    author_email="anton.m.alexeye@gmail.com",
    url="https://github.com/alexeyev/apertium2ud",
    keywords=["natural language processing", "apertium", "morphology"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Topic :: Text Processing",
    ],
    zip_safe=False,
    include_package_data=False,
    python_requires=">=3.7",
)
