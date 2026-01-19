from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="cpp-to-java-converter",
    version="2.0.0",
    author="AI Assistant",
    author_email="assistant@example.com",
    description="A C++ to Java source code converter using libclang for AST parsing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/cpp-to-java-converter",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "libclang>=12.0.0",
        "streamlit>=1.28.0",
        "typing-extensions>=4.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cpp-to-java-converter=cli:main",
        ],
    },
)