from setuptools import setup, find_packages
import os

version = '0.1'

setup(name='hl.plone.boardnotifications',
      version=version,
      description="Notify users when Ploneboard threads or comments are modified",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Framework :: Plone",
        "Programming Language :: Python",
        ],
      keywords='Plone Ploneboard board forum notifications',
      author='Thomas Schorr',
      author_email='thomas.schorr@haufe-lexware.com',
      url='https://github.com/Haufe-Lexware/hl.plone.boardnotifications',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['hl', 'hl.plone'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'Products.Ploneboard >= 3.0',
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-

      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
