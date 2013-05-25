"""
setup.py
"""
from setuptools import setup

setup (
    name='corun',
    version='0.1.0',
    author='Rodney Gomes',
    author_email='rodneygomes@gmail.com',
    url='',
    install_requires = ["setuptools"],
    test_suite="tests",
    keywords = ['coroutine'],
    py_modules = ['corun'],
    license='Apache 2.0 License',
    description='coroutine library',
    long_description=''
)
