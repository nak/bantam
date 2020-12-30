.. bantam documentation master file, created by
   sphinx-quickstart on Tue Dec 29 14:23:26 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Bantam's Documentation!
==================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:



Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Introduction
============

.. automodule:: bantam.web

The specific WebApplication API is simple, and only the *start* method is of importance:

.. autoclass:: bantam.web.WebApplication
    :members: DuplicateRoute, start


Client-Side Code Generation
---------------------------

.. automodule:: bantam.js


Optional Parameters
-------------------

If default parameter values are provided, they are optionally provided on the javascript client-side as well.
Additionally, to refine the second rule of declaring a web API above, the type for a parameter can also be
declared as an Optional to any the types declared there. Provided a default value, include *None*, is provided.

