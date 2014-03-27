
import sys, os

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
]
templates_path = ['sphinx-templates']
source_suffix = '.rst'
master_doc = 'index'

project = u'normalize'
copyright = u'2014, Sam Vilain, Hearsay Social'

version = '0.1'
release = '0.0.4'

exclude_patterns = ['sphinx-build']
pygments_style = 'sphinx'
html_theme = 'default'

html_static_path = ['sphinx-static']
htmlhelp_basename = 'normalizedoc'

latex_elements = {}
latex_documents = [
    ('index', 'normalize.tex', u'normalize Documentation',
     u'Sam Vilain, Hearsay Social', 'manual'),
]

man_pages = [
    ('index', 'normalize', u'normalize Documentation',
     [u'Sam Vilain, Hearsay Social'], 1)
]

texinfo_documents = [
  ('index', 'normalize', u'normalize Documentation',
   u'Sam Vilain, Hearsay Social', 'normalize',
   'Declarative Python meta-model system and visitor utilities',
   'Object-Oriented Programming'),
]



