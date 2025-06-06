from setuptools import setup, find_packages

setup(
    name="rally",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'flask',
        'flask-socketio',
        'flask-cors',
        'python-dotenv',
    ],
) 