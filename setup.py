from setuptools import setup, find_packages

setup(
    name="bb-core",
    version="0.1.6",
    description="Core package for the brickblock library.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Erfan",
    author_email="erfanvaredi@gmail.com",
    url="https://github.com/erfanvaredi/bb-core",  # Update with your repository URL
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=[
        # Add your dependencies here
        # 'pickle',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",  # Update with your license
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10',
)

