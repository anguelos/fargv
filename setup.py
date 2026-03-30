#import setuptools
from setuptools import setup, Extension

# Read version from the single source of truth
_version = {}
with open('fargv/version.py') as _f:
    exec(_f.read(), _version)

setup(
    name='fargv',
    version=_version['__version__'],
    packages=['fargv'],
    license='MIT',
    author='Anguelos Nicolaou',
    author_email='anguelos.nicolaou@gmail.com',
    url='https://github.com/anguelos/fargv',
    description="A very easy to use argument parser.",
    long_description_content_type="text/markdown",
    long_description=open('README.md').read(),
    # download_url = 'https://github.com/anguelos/fargv/archive/0.1.3.tar.gz',
    keywords = ["argv", "CLI", "argument", "GUI", "parser", "command", "line", "interface"],
    classifiers=[
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering"],
    install_requires=[],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
        ],
        "docs": [
            "sphinx",
            "sphinx-rtd-theme",
            "myst-parser",
            "sphinx-copybutton",
        ],
    },
)
