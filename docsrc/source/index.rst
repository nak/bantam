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

.. automodule:: bantam

The specific WebApplication API is simple, and only the *start* method is of importance:

.. autoclass:: bantam.http.WebApplication
    :members: DuplicateRoute, start

Of particular interest is the modules parameter of the start method.  This determines which modules and therefore
which classes and their the @web_api definitions are loaded.

Allowed Type Annotations
========================

Being http-based, the magic behind the scenes in abstracting the HTTP protocol away from the client occurs through
json serialization and deserialization.  This means that only certain type hints are allowed in the signature of a
method decorated with @web_api:

#. The basic builtins of *int*, *float*, *str*, *bool*
#. For arguments, the builtins of *list*, *set*, *tuple* and *dict*; the return type must be explicit
   (e.g. *Dict[Union[int, str]]*),as the system must know the type when converting fom a generic json string
#. Anything hat is decorated with @dataclass and whose element types meet these criteria (recursively)
#. Any typing *Dict*, *List*, *Set*, *Tuple*, provided the (key and) element type recursively meet these criteria
#. Use of *Union* and *Optional* are allowed

All arguments and the return type must be explicitly specified in the signature of @web_api-decorated methods.

Client-Side Code Generation
===========================

As an even greater convenience,
Bantam provides means of auto-generating both javascript and client code to interact with a bantam-enabled application.
Javascript in particular can be generate on-the-fly and served upon startup.

Javascript
----------

the code can be generated on the fly, when the *WebApplication* is created.
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

Furthermore, the web api that is registered is also directly callable as a Python function.  This engenders the
concept of "library-as-a-service", where the code can act directly as a library or as a distributed Rest-ful
service transparently to the caller.

To provide more detail on what this generation look like:


.. automodule:: bantam.js


Python
------

.. automodule:: bantam.client

Advanced Discussion on Parameters
=================================

Optional Parameters
-------------------

If default parameter values are provided, they are optionally provided on the javascript client-side as well.
Additionally, to refine the second rule of declaring a web API above, the type for a parameter can also be
declared as an Optional to any the types declared there. Provided a default value, include *None*, is provided.

Streamed Responses
------------------

Responses can be streamed back to the client.  To do so, the underlying Python server call must be written as
an *AsyncGenerator*, returning a type *AsyncGenerator[None, <int, float, bool, str, or bytes>]*.   (Thus, ammending
the rule of allowed return values above).  Consider this example of a PoetryReader class:

.. code-block:: python
    :caption: Example of server code to stream a poem back to the client

    import asyncio
    import os

    from bantam.decorators import RestMethod
    from bantam.web import WebApplication, web_api
    from typing import AsyncGenerator

    class PoetryReader:
        POEM = """
        Mary had a little lamb...
        Its fleece was white as snow...
        Everywhere that Mary went...
        Her lamb was sure to go...
        """

        @classmethod
        @web_api(content_type='text/streamed', method=RestMethod.POST)
        async def read_poem(cls) -> AsyncGenerator[None, str]:
            for line in PoetryReader.POEM.strip().splitlines():
                yield line
                await asyncio.sleep(2)  # for dramatic effect
            yield "THE END"
            await asyncio.sleep(2)

    if __name__ == '__main__':
        app = WebApplication(static_path=os.path.dirname(__file__), js_bundle_name='poetry_reader')
        asyncio.get_event_loop().run_until_complete(app.start())  # default to localhost HTTP on port 8080


.. caution::
    The method must be declared as POST to work consistently across different machines/web browsers


The javascript generated for such an API is the same, with the exception that the *onsuccess* callback will be
named *onreceive* and will be called with two parameters.  The first is the "chunk" that is read and the second
is a boolean indicating whether it is the final one or not.  The "chunks" are determine by the type yielded by
the generator:

* for numeric or *bool* types: each number yielded will invoke a single callback to *onreceive*.  But be aware that multiple
     values can be sent at a time and that the generated javascript code will handle the logic to split them up.
     This is particularly true when there is no or short sleep periods between yields.
* for *str* type: *onreceive* will be called for each line received, guaranteeing whole lines are provided
* for *bytes* type: *cnreceive* will be called for each chunk of bytes received, regardless of size

Here is a bit of HTML to implement the client-side:

.. code-block:: html
   :caption: HTML containing client-side code for handling streaming responses

    <html>
    <head>
        <script src="/static/js/poetry_reader.js" ></script>
    </head>
    <body>
    <div id='poem'></div>
    <script>
        document.addEventListener('DOMContentLoaded', function(event) {

            let reader = new bantam.__main__.PoetryReader("http://localhost:8080");
            let html = ""
            let onreceive = function(line, is_done){
                 html += "<p>" + line + "</p><br/>";
                 document.getElementById('poem').innerHTML = html;
            }
            reader.read_poem(onreceive, function(code, reason){
                alert("UNEXPECTED ERROR OCCURRED: " + code + " : " + reason);
            });
        });
    </script>
    </body>
    </html>

Loading the page http://localhost:8080/static/index.html will execute the code.

Streamed Requests
-----------------
You can also make requests that stream (upload) data to the server.  Here again, we add two more (final) allowable
types for parameters that specify a parameter provides an (async) iterator for lopping over and sending data chunk
by chunk:

* *bantam.web.AsyncLineGIterator*: specifies that the client will send *str* data to the server line by line (without
  any return character present in the line)
* *bantam.web.AsyncChunkIterator*: specifies that the iterator will send *bytes* of data to the server

.. caution::
   At most one parameter may be specified as an iterator type

Here is what a web API method would look like that captures uploaded byts of data to a file and reports progress
back to the client:

.. code-block:: python
   :caption: Example code for Python web API method that streams data

    class Uploader:
        @classmethod
        @web_api(content_type='text/html')
        async def receive_streamed_data(cls, size: int, byte_data: AsyncChunkGenerator) -> AsyncGenerator[None, float]
            bytes_received: int = 0
            packet_size = 100 # bytes
            with open('some_file_path', 'bw') as f:
                async for data in byte_data(packet_size):
                    f.write(byte_data)
                    bytes_received += len(byte_data)
                    progress = bytes_received*100/size
                    yield progress


As a side note, when a streaming parameter is specified, all others will be sent as query parameters even when the request is
POST.  Note that for chunk iterators, the parameter byte_data will be a callable that takes a single parameter,
which is the max size of packet to be read each chunk.  The line iterator will be a simple iterator, not a callable.
That is for a line itertor the Python code would look like:

.. code-block:: python

    ...
    class Uploader:
        @classmethod
        @web_api(content_type='text/html')
        async def receive_streamed_data(cls, size: int, line_by_line: AsyncLineGenerator) -> AsyncGenerator[None, float]
            ...
            with open('some_file_path', 'bw') as f:
                async for data in line_by_line:  #<====  NOT a function call as in AsyncChunkIterator
                   ...


On the client side, the signature of the API will look similar, with the *onsuccess* (*onreceive* if the
response is also streaming) and *onerror* callbacks act the same.  The differences are that:

#. the parameter that is the AsyncLine[Chunk]Iterator will not be present in the signature
#. insted, the javascript API call will return a function to be called by the client to send each chunk of data (ad
   the first and only parameter of the function)

An example of uploading a file using the above api (assuming the Uploader class belongs to the module *uploads*):

.. code-block:: javascript

     ...
     let onreceive = function(progress, is_done){
        ...
     }
     let onerror = function(code, reason){
        ...
     }
     let uploader = bantam.uploads.Uploader(site_url)
     let size_of_upload = 1024*1024;  // bytes
     let send_byte_data = uploader.receive_streamed_data(onreceive, onerror, size_of_upload)
     const reader = new FileReader();
     reader.addEventListener('load', (event) => {
         send_byte_data(event.target.result);
     });
     reader.readAsText(file); // assumng file is a file object created prior to this code


Pre/Post-Processing Request/Responses
=====================================

You can pre-process requests before a call is made to the underlying Python web API. Likewise, you can modify
responses returned from a Python web API call before it is sent to the client.  There are two means to do so.
One is at the application level, by calling *set_preprocessor* and *set_postprocessor* accordingly:

.. code-block:: python

   def preprocessor(request: Request) -> Union[None, Dict[str, Any]]:
      return {'additional_arg': "value"}  # adds an additional argument to the web API call; can also return None

   def postprocessor(response: Response) -> None:
      response.body += b"\n Additional line of output"

   ...

   app = WebApplication(...)
   app.set_preprocessing(preprocessor)
   app.set_postprocessing(postprocessor)


Alternatively, you can do this for each individual web API method through optional *preprocess* and *postprocess*
arguments.  Using the above define *prerprocessor* and *postprocessor* functions, this would look like:

.. code-block:: python

   ...
   @web_api(content_type='text/plain', preprocess=preprocessor, postprocess=postprocessor)



Getting Request Context
=======================
In the implementation of a web api, you can get the context of the rquest (i.e., the request headers).  Such
information may be useful if chaining one Rest call to other backend Rest calls in a service hiearchy, and passing
any contextual information around the originating request down through such a chain of calls.  Context is available
through the *WebApplication.get_context()* call which returns a dictionary of the reques header keys and values.

Be aware that accessing context may limit the use of your code as a "library-as-a-service".  If a direct call is made
to a web api without any request, the *get_context()* call will return None, a case you should consider handling.