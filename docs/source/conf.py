# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Ormophine'
copyright = '2026, M.J.Nazify.Yummy'
author = 'M.J.Nazify.Yummy'
release = '0.7.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

import os
import sys

# ============================================================
# مسیر ریشه پروژه رو به sys.path اضافه کن
# ============================================================
sys.path.insert(0, r'D:\Ormophine-Source\Ormophine')  # ← این رو با مسیر خودت عوض کن
# ============================================================

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    # 'sphinx_autodoc_typehints',  # اگه نصب کردی، کامنتش رو بردار
]

templates_path = ['_templates']
exclude_patterns = []

autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'private-members': False,
    'special-members': '__init__, __add__, __radd__, __sub__, __rsub__, __mul__, __rmul__, __pow__, __rpow__, __truediv__, __rtruediv__, __mod__, __rmod__, __getitem__, __eq__, __ne__, __gt__, __lt__, __ge__, __le__, __and__, __or__, __hash__',
    'exclude-members': '__weakref__, __dict__, __module__, __annotations__, __doc__',
    'show-inheritance': True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_param = True
napoleon_use_rtype = True

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent  # این به D:\Ormophine-Source می‌رسد
sys.path.insert(0, str(PROJECT_ROOT))