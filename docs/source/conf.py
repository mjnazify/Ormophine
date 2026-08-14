import os
import sys

# -- Project information -----------------------------------------------------
project = 'Ormophine'
copyright = '2026, M.J.Nazify.Yummy'
author = 'M.J.Nazify.Yummy'
release = '0.8.1'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode'
]
DOCS_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(DOCS_DIR, '..', '..'))

sys.path.insert(0, PROJECT_ROOT)

autodoc_mock_imports = [
    'MySQLdb', 
    'mysqlclient', 
    'psycopg2', 
    'psycopg2_binary',
    'psycopg'  
]

autodoc_member_order = 'bysource'
autodoc_class_signature = 'separated'
autodoc_typehints = 'description'

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

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'