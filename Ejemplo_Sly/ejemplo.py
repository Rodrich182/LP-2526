from sly import Lexer
from sly import Parser

class XMLLexer(Lexer):
    tokens = { TAG_OPEN, TAG_CLOSE, NAME, TEXT }
    
    ignore = ' \t'

    # <tag>
    TAG_OPEN = r'<[a-zA-Z_:][a-zA-Z0-9._:-]*>'
    # </tag>
    TAG_CLOSE = r'</[a-zA-Z_:][a-zA-Z0-9._:-]*>'
    # Texto entre etiquetas
    TEXT = r'[^<>]+'
    
    # Extrae el nombre de la etiqueta
    @_(r'[a-zA-Z_:][a-zA-Z0-9._:-]*')
    def NAME(self, t):
        return t




class XMLParser(Parser):
    tokens = XMLLexer.tokens

    # Regla inicial
    @_('element')
    def document(self, p):
        return p.element

    @_('TAG_OPEN content TAG_CLOSE')
    def element(self, p):
        tag = p.TAG_OPEN[1:-1]        # extraemos el nombre
        close_tag = p.TAG_CLOSE[2:-1]
        
        if tag != close_tag:
            raise SyntaxError(f"Etiqueta abierta <{tag}> no coincide con </{close_tag}>")
        
        return ("tag", tag, p.content)

    @_('content element',
       'content TEXT')
    def content(self, p):
        return p.content + [p.element] if hasattr(p, 'element') else p.content + [p.TEXT]

    @_('')
    def content(self, p):
        return []

if __name__ == '__main__':
    lexer = XMLLexer()
    parser = XMLParser()

    xml_input = "<greeting>Hello, <name>World</name>!</greeting>"
    tokens = lexer.tokenize(xml_input)
    
    for token in tokens:
        print(token)

    result = parser.parse(lexer.tokenize(xml_input))
    print(result)
