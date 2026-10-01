from app.knowledge.parsers import MarkdownParser, TextParser, get_parser


def test_text_parser():
    parser = get_parser("text/plain", "test.txt")
    assert isinstance(parser, TextParser)

    content = b"Hello world"
    text, meta = parser.parse(content)
    assert text == "Hello world"
    assert meta["format"] == "txt"

def test_markdown_parser():
    parser = get_parser("text/markdown", "test.md")
    assert isinstance(parser, MarkdownParser)

    content = b"# Title\n\nBody"
    text, meta = parser.parse(content)
    assert text == "# Title\n\nBody"
    assert meta["format"] == "markdown"
