from setuptools import setup, find_packages

setup(
    name="bb-core",
    version="0.1.18",
    description="Core package for the brickblock library.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Erfan",
    author_email="erfanvaredi@gmail.com",
    url="https://github.com/erfanvaredi/brickblock",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        # Add dependencies here
        # 'pickle',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
