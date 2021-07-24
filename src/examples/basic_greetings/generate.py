from bantam.js import JavascriptGenerator
from salutations import Greetings  # noqa

if __name__ == '__main__':
    with open('greetings.js', 'bw') as output:
        JavascriptGenerator.generate(out=output, skip_html=False)
