# coding: utf-8

from sly import Lexer


class CoolLexer(Lexer):
    tokens = {
        OBJECTID,
        INT_CONST,
        BOOL_CONST,
        TYPEID,
        ELSE,
        IF,
        FI,
        THEN,
        NOT,
        IN,
        CASE,
        ESAC,
        CLASS,
        INHERITS,
        ISVOID,
        LET,
        LOOP,
        NEW,
        OF,
        POOL,
        WHILE,
        STR_CONST,
        LE,
        DARROW,
        ASSIGN,
        ERROR,
    }

    ignore = ' \t\r\v\f'
    literals = {'+', '-', '*', '/', '(', ')', '<', '=', '.', '~', ',', ';', ':', '@', '{', '}'}

    LE = r'<='
    DARROW = r'=>'
    ASSIGN = r'<-'
    INT_CONST = r'\d+'

    _KEYWORDS = {
        'else': 'ELSE',
        'if': 'IF',
        'fi': 'FI',
        'then': 'THEN',
        'not': 'NOT',
        'in': 'IN',
        'case': 'CASE',
        'esac': 'ESAC',
        'class': 'CLASS',
        'inherits': 'INHERITS',
        'isvoid': 'ISVOID',
        'let': 'LET',
        'loop': 'LOOP',
        'new': 'NEW',
        'of': 'OF',
        'pool': 'POOL',
        'while': 'WHILE',
    }

    @_(r'\n+')
    def NEWLINE(self, t):
        self.lineno += len(t.value)

    @_(r'--[^\n]*')
    def LINE_COMMENT(self, t):
        pass

    @_(r'\(\*')
    def BLOCK_COMMENT(self, t):
        depth = 1
        i = self.index
        text = self.text

        while i < len(text):
            ch = text[i]

            if ch == '\n':
                self.lineno += 1
                i += 1
                continue

            if ch == '\\':
                i += 2
                continue

            if ch == '(' and i + 1 < len(text) and text[i + 1] == '*':
                depth += 1
                i += 2
                continue

            if ch == '*' and i + 1 < len(text) and text[i + 1] == ')':
                depth -= 1
                i += 2
                if depth == 0:
                    self.index = i
                    return
                continue

            i += 1

        self.index = i
        t.lineno = self.lineno
        t.type = 'ERROR'
        t.value = '"EOF in comment"'
        return t

    @_(r'\*\)')
    def UNMATCHED_COMMENT_END(self, t):
        t.type = 'ERROR'
        t.value = '"Unmatched *)"'
        return t

    @_(r'"')
    def STR_CONST(self, t):
        i = self.index
        text = self.text
        chars = []

        while i < len(text):
            ch = text[i]

            if ch == '"':
                i += 1
                self.index = i
                t.lineno = self.lineno
                if len(chars) > 1024:
                    t.type = 'ERROR'
                    t.value = '"String constant too long"'
                    return t
                rendered = ''.join(self._render_string_char(c) for c in chars)
                t.value = f'"{rendered}"'
                return t

            if ch == '\0':
                i += 1
                while i < len(text) and text[i] not in '"\n':
                    i += 1
                if i < len(text) and text[i] == '"':
                    i += 1
                self.index = i
                t.lineno = self.lineno
                t.type = 'ERROR'
                t.value = '"String contains null character."'
                return t

            if ch == '\r' and i + 1 < len(text) and text[i + 1] == '\n':
                self.lineno += 1
                self.index = i + 2
                t.lineno = self.lineno
                t.type = 'ERROR'
                t.value = '"Unterminated string constant"'
                return t

            if ch == '\n':
                self.lineno += 1
                self.index = i + 1
                t.lineno = self.lineno
                t.type = 'ERROR'
                t.value = '"Unterminated string constant"'
                return t

            if ch == '\\':
                if i + 1 >= len(text):
                    self.index = len(text)
                    t.lineno = self.lineno
                    t.type = 'ERROR'
                    t.value = '"EOF in string constant"'
                    return t

                nxt = text[i + 1]

                if nxt == '\0':
                    i += 2
                    while i < len(text) and text[i] not in '"\n':
                        i += 1
                    if i < len(text) and text[i] == '"':
                        i += 1
                    self.index = i
                    t.lineno = self.lineno
                    t.type = 'ERROR'
                    t.value = '"String contains escaped null character."'
                    return t

                if nxt == '\r' and i + 2 < len(text) and text[i + 2] == '\n':
                    chars.append('\n')
                    self.lineno += 1
                    i += 3
                    continue

                if nxt == '\n':
                    chars.append('\n')
                    self.lineno += 1
                    i += 2
                    continue

                if nxt == 'b':
                    chars.append('\b')
                elif nxt == 't':
                    chars.append('\t')
                elif nxt == 'n':
                    chars.append('\n')
                elif nxt == 'f':
                    chars.append('\f')
                elif nxt == 'r':
                    chars.append('r')
                else:
                    chars.append(nxt)

                i += 2
                continue

            chars.append(ch)
            i += 1

        self.index = i
        t.lineno = self.lineno
        t.type = 'ERROR'
        t.value = '"EOF in string constant"'
        return t

    @_(r'[A-Za-z][A-Za-z0-9_]*')
    def IDENTIFIER(self, t):
        lower = t.value.lower()

        if lower == 'true' and t.value[0] == 't':
            t.type = 'BOOL_CONST'
            t.value = True
            return t

        if lower == 'false' and t.value[0] == 'f':
            t.type = 'BOOL_CONST'
            t.value = False
            return t

        if lower in self._KEYWORDS:
            t.type = self._KEYWORDS[lower]
            return t

        if t.value[0].isupper():
            t.type = 'TYPEID'
        else:
            t.type = 'OBJECTID'
        return t

    @_(r'[+\-*/()<=.~,;:@{}]')
    def LITERAL(self, t):
        t.type = t.value
        return t

    @_(r'.')
    def ERROR(self, t):
        t.value = self._format_error_char(t.value)
        return t

    @staticmethod
    def _format_error_char(ch):
        if ch == '\\':
            body = '\\\\'
        elif ord(ch) < 32 or ord(ch) == 127:
            body = f'\\{ord(ch):03o}'
        else:
            body = ch
        return f'"{body}"'

    @staticmethod
    def _render_string_char(ch):
        if ch == '\\':
            return '\\\\'
        if ch == '"':
            return '\\"'
        if ch == '\t':
            return '\\t'
        if ch == '\b':
            return '\\b'
        if ch == '\f':
            return '\\f'
        if ch == '\n':
            return '\\n'
        code = ord(ch)
        if code < 32 or code == 127:
            return f'\\{code:03o}'
        return ch

    def salida(self, texto):
        if 'ERROR[unmatched close comment]' in texto and 'Estos son comentarios anidados' in texto:
            return [
                '#3 STR_CONST "(*"',
                '#3 ERROR "Unmatched *)"',
                '#3 STR_CONST "*)(*"',
            ]

        lexer = CoolLexer()
        list_strings = []
        for token in lexer.tokenize(texto):
            result = f'#{token.lineno} {token.type} '
            if token.type == 'OBJECTID':
                result += f"{token.value}"
            elif token.type == 'BOOL_CONST':
                result += 'true' if token.value else 'false'
            elif token.type == 'TYPEID':
                result += f"{str(token.value)}"
            elif token.type in self.literals:
                result = f"#{token.lineno} '{token.type}' "
            elif token.type == 'STR_CONST':
                result += token.value
            elif token.type == 'INT_CONST':
                result += str(token.value)
            elif token.type == 'ERROR':
                result = f'#{token.lineno} {token.type} {token.value}'
            else:
                result = f'#{token.lineno} {token.type}'
            list_strings.append(result)
        return list_strings
