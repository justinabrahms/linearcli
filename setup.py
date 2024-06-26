from setuptools import setup, find_packages

setup(
    name = "linearcli",
    version = "1.0.1",
    author = "Mike Lyons",
    author_email = "mdl0394@gmail.com",
    license = "MIT",
    description = "Simple CLI interface for linear task manager (https://linear.app)",
    long_description = "",
    url = "https://github.com/frenchie4111/linearcli",
    py_modules = [
        "linearcli"
    ],
    packages = find_packages(),
    install_requires = [
        "requests",
    ],
    python_requires=">=3.8",
    entry_points = """
        [console_scripts]
        linear=linearcli.linear:main
    """
)
