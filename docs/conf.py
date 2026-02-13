import os
import sys
from pathlib import Path
from sphinx.ext import apidoc

# see https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html
sys.path.insert(0, str(Path("..").resolve()))

# automatically generate documentation for these modules by invoking 'sphinx-apidoc'
project_dir = Path(__file__).parent.parent
output_dir = os.path.join(project_dir, "docs/api")
apidoc.main(["-o", str(output_dir), str(project_dir)])

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "OKR-Tool"
copyright = "2026, Bnyro, KaanElman, Musti0611, Javes64, Hasi73jac"
author = "Bnyro, KaanElman, Musti0611, Javes64, Hasi73jac"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosummary",
]

autosummary_generate = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
