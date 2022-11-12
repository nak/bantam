"""
Welcome to Bantam, a framework for running a web server, built on top of *aiohttp*,
poviding a convience-layer of abstraction.
The framework allows users to define a Python web API through static methods of classes,
and allows auto-generation of corresponding javascript APIs to match.  The developer need not
be concerned about the details of how to map routes nor to understand the details of HTTP transactions.
Ths developer need only focus on development of a web API as a Python interface.

Getting Started
---------------

Let's look at setting up a simple WebApplication on your localhost:

>>> import asyncio
... from bantam.http import web_api, RestMethod, WebApplication
...
... class Greetings:
...
...     @web_api(content_type='text/html', method=RestMethod.GET)
...     @staticmethod
...     async def welcome(name: str) -> str:
...         \"\"\"
...         Welcome someone
...
...         :@param name: name of person to greet
...         :return: a salutation of welcome
...         \"\"\"
...         return f"<html><body><p>Welcome, {name}!</p></body></html>"
...
...     @web_api(content_type='text/html', method=RestMethod.GET)
...     @classmethod
...     async def goodbye(cls, type_of_day: str) -> str:
...         \"\"\"
...         Tell someone goodbye by telling them to have a day (of the given type)
...
...         :@param type_of_day:  an adjective describe what type of day to have
...         :return: a saltation of welcome
...         \"\"\"
...         return f"<html><body><p>Have a {type_of_day} day!</p></body></html>"
...
... if __name__ == '__main__':
...     app = WebApplication()
...     asyncio.run(app.start()) # default to localhost HTTP on port 8080

Saving this to a file, 'salutations.py', you can run this start your server:

.. code-block:: bash

    % python3 salutations.py

Then open a browser to the following URL's:

* http://localhost:8080/Greetings/welcome?name=Bob
* http://localhost:8080/Greetings/goodbye?type_of_day=wonderful

to display various salutiations.

To explain this code, the *@web_api* decorator declares a method that is mapped to a route. The route is determined
by the class name, in this case *Greetings*, and the method name. Thus, the "welcome" method above, as a member of
*Greetings* class, is mapped to the route '/Greetings/welcome".  There are some rules about methods declared as
*@web_api*:

#. They can be @staticmethods, @classmethods or even instance methods (explained below), but @classmethod or
   instance methods are prefered
#. They must provide all type hints for parameters and return value.  The types must
   be of only specific kinds as explained below
#. Be judicious on GET vs POST, particuraly being mindfl of the amount of data to be passed in parameters as
   wll as returned.  Large data transfers should use POST

The query parameters provided in the full URL are mapped to the parameters in the Python method.  For example,
the query parameter name=Box in the first URL above maps to the *name* parameter of the *Greetings.welcome* method,
with 'Bob' as the value.
The query parameters are translated to the value and type expected by the
Python API. If the value is not convertible to the proper type, an error code along with reason are returned.
There are a few other options for parameters and return type that will be  discussed later on streaming.

The methods can also be declared as POST operations.  In this case, parameter values would be sent as part of the
payload of the request (not query parameters) as a simple JSON dictionary.

.. caution::

    Although the code prevents name collisions, the underlying (automated) routes do not, and a route must be unique.
    Thus, each pair of class/method declared as a @web_api must be unique, even across differing modules.

"""


class HTTPException(Exception):

    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self._code = code

    @property
    def status_code(self):
        return self._code
