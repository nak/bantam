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

Generation on the fly
*********************

As an even greater convenience, the code can be generated on the fly, when the *WebApplication* is created.
By providing two parameters to the init call to your *WebApplication*:

* *static_path*: the root path to serve static files
* *js_bundle_name*: the name (**without** extension) of the javascript bundle file

the javascript code will be (re)generated just before startup of the server.  The javascript file that provides
the web API on the client side will then be available under the static route */static/js/<js-bundle-name>.js*.

In the example above the instantiations of the *app* would be:

.. code-block:: python

    app = WebApplication(static_path=Path("./static"), js_bundle_name='salutations')

The client interface is then available through:

* http://localhost:8080/static/js/salutations.js


Through a simple normal declaration of an API in the Python code, and auto-generation of client code, the developer
is free to ignore the details of the inner works of routes and HTTP transactions.


Optional Parameters
-------------------

If default parameter values are provided, they are optionally provided on the javascript client-side as well.
Additionally, to refine the second rule of declaring a web API above, the type for a parameter can also be
declared as an Optional to any the types declared there. Provided a default value, include *None*, is provided.

Streamed Responses
------------------

