import asyncio
from bantam.web import web_api, RestMethod, WebApplication


class Greetings:

    @web_api(content_type='text/html', method=RestMethod.GET)
    @staticmethod
    async def welcome(name: str) -> str:
        """
        Welcome someone

        :param name: name of person to greet
        :return: a salutation of welcome
        """
        return f"<html><body><p>Welcome, {name}!</p></body></html>"

    @web_api(content_type='text/html', method=RestMethod.GET)
    @staticmethod
    async def goodbye(type_of_day: str) -> str:
        """
        Say goodbye by telling someone to have a day (of the given type)

        :param type_of_day: adjective describing type of day to have
        :return: a goodby message
        """
        return f"<html><body><p>Have a {type_of_day} day!</p></body></html>"


if __name__ == '__main__':
    app = WebApplication()
    asyncio.get_event_loop().run_until_complete(app.start()) # default to localhost HTTP on port 8080
