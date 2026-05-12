# coding: utf-8

from Lexer import CoolLexer
from sly import Parser
from Clases import *


class CoolParser(Parser):
    tokens = CoolLexer.tokens
    debugfile = 'salida.out'

    def __init__(self):
        self.errores = []
        self.nombre_fichero = ''

    # ------------------------------------------------------------------
    # Precedencia (de menor a mayor, segun el manual de COOL)
    # ------------------------------------------------------------------
    precedence = (
        ('right', ASSIGN),
        ('left', NOT),
        ('nonassoc', '=', LE, '<'),
        ('left', '+', '-'),
        ('left', '*', '/'),
        ('right', ISVOID),
        ('right', '~'),
        ('left', '@'),
        ('left', '.'),
    )

    # ==================================================================
    # Regla inicial: Programa = una o mas clases
    # ==================================================================

    @_('clases')
    def programa(self, p):
        return Programa(linea=p.clases[-1].linea, secuencia=p.clases)

    @_('clases basura')
    def programa(self, p):
        if len(self.errores) == 1:
            self.errores.clear()
        return Programa(linea=p.clases[-1].linea, secuencia=p.clases)

    @_('basura error')
    def basura(self, p):
        return None

    @_('error')
    def basura(self, p):
        return None

    # ==================================================================
    # Lista de clases (una o mas)
    # ==================================================================

    @_('clases clase')
    def clases(self, p):
        return p.clases + [p.clase]

    @_('clase')
    def clases(self, p):
        return [p.clase]

    # ==================================================================
    # Clase: CLASS TYPEID [INHERITS TYPEID] { caract* } ;
    # ==================================================================

    @_('CLASS TYPEID "{" caracteristicas "}" ";"')
    def clase(self, p):
        return Clase(linea=p._slice[5].lineno, nombre=p.TYPEID, padre='Object',
                     nombre_fichero=self.nombre_fichero,
                     caracteristicas=p.caracteristicas)

    @_('CLASS TYPEID INHERITS TYPEID "{" caracteristicas "}" ";"')
    def clase(self, p):
        return Clase(linea=p._slice[7].lineno, nombre=p.TYPEID0, padre=p.TYPEID1,
                     nombre_fichero=self.nombre_fichero,
                     caracteristicas=p.caracteristicas)

    @_('CLASS TYPEID error "{" caracteristicas "}" ";"')
    def clase(self, p):
        return Clase(linea=p._slice[5].lineno, nombre=p.TYPEID, padre='Object',
                     nombre_fichero=self.nombre_fichero,
                     caracteristicas=p.caracteristicas)

    # ==================================================================
    # Lista de caracteristicas (puede ser vacia)
    # ==================================================================

    @_('caracteristicas caracteristica')
    def caracteristicas(self, p):
        return p.caracteristicas + [p.caracteristica]

    @_('caracteristicas error ";"')
    def caracteristicas(self, p):
        return p.caracteristicas

    @_('')
    def caracteristicas(self, p):
        return []

    # ==================================================================
    # Metodo: OBJECTID ( [formales] ) : TYPEID { expr } ;
    # ==================================================================

    @_('OBJECTID "(" ")" ":" TYPEID "{" expr "}" ";"')
    def caracteristica(self, p):
        return Metodo(linea=p._slice[8].lineno, nombre=p.OBJECTID, tipo=p.TYPEID,
                      cuerpo=p.expr, formales=[])

    @_('OBJECTID "(" formales ")" ":" TYPEID "{" expr "}" ";"')
    def caracteristica(self, p):
        return Metodo(linea=p._slice[9].lineno, nombre=p.OBJECTID, tipo=p.TYPEID,
                      cuerpo=p.expr, formales=p.formales)

    # ==================================================================
    # Atributo: OBJECTID : TYPEID [ <- expr ] ;
    # ==================================================================

    @_('OBJECTID ":" TYPEID ";"')
    def caracteristica(self, p):
        return Atributo(linea=p._slice[3].lineno, nombre=p.OBJECTID, tipo=p.TYPEID,
                        cuerpo=NoExpr(linea=p._slice[3].lineno))

    @_('OBJECTID ":" TYPEID ASSIGN expr ";"')
    def caracteristica(self, p):
        return Atributo(linea=p._slice[5].lineno, nombre=p.OBJECTID, tipo=p.TYPEID,
                        cuerpo=p.expr)

    # ==================================================================
    # Formales: formal (, formal)*
    # ==================================================================

    @_('formales "," formal')
    def formales(self, p):
        return p.formales + [p.formal]

    @_('formales ";" formal')
    def formales(self, p):
        self.errores.append(
            f'"{self.nombre_fichero}", line {p.lineno}: '
            "syntax error at or near ';'"
        )
        return p.formales + [p.formal]

    @_('formal')
    def formales(self, p):
        return [p.formal]

    @_('OBJECTID ":" TYPEID')
    def formal(self, p):
        return Formal(linea=p.lineno, nombre_variable=p.OBJECTID, tipo=p.TYPEID)

    # ==================================================================
    # Expresiones
    # ==================================================================

    # --- Asignacion: OBJECTID <- expr ---
    @_('OBJECTID ASSIGN expr')
    def expr(self, p):
        return Asignacion(linea=p.lineno, nombre=p.OBJECTID, cuerpo=p.expr)

    # --- Operaciones aritmeticas ---
    @_('expr "+" expr')
    def expr(self, p):
        return Suma(linea=p.lineno, izquierda=p.expr0, derecha=p.expr1)

    @_('expr "-" expr')
    def expr(self, p):
        return Resta(linea=p.lineno, izquierda=p.expr0, derecha=p.expr1)

    @_('expr "*" expr')
    def expr(self, p):
        return Multiplicacion(linea=p.lineno, izquierda=p.expr0, derecha=p.expr1)

    @_('expr "/" expr')
    def expr(self, p):
        return Division(linea=p.lineno, izquierda=p.expr0, derecha=p.expr1)

    # --- Comparaciones ---
    @_('expr "<" expr')
    def expr(self, p):
        return Menor(linea=p.lineno, izquierda=p.expr0, derecha=p.expr1)

    @_('expr LE expr')
    def expr(self, p):
        return LeIgual(linea=p.lineno, izquierda=p.expr0, derecha=p.expr1)

    @_('expr "=" expr')
    def expr(self, p):
        return Igual(linea=p.lineno, izquierda=p.expr0, derecha=p.expr1)

    # --- Parentesis ---
    @_('"(" expr ")"')
    def expr(self, p):
        return p.expr

    # --- NOT logico ---
    @_('NOT expr')
    def expr(self, p):
        return Not(linea=p.lineno, expr=p.expr)

    # --- isvoid ---
    @_('ISVOID expr')
    def expr(self, p):
        return EsNulo(linea=p.lineno, expr=p.expr)

    # --- Negacion aritmetica ~ ---
    @_('"~" expr')
    def expr(self, p):
        return Neg(linea=p.lineno, expr=p.expr)

    # --- Dispatch estatico: expr@TYPEID.OBJECTID(...) ---
    @_('expr "@" TYPEID "." OBJECTID "(" ")"')
    def expr(self, p):
        return LlamadaMetodoEstatico(linea=p.lineno, cuerpo=p.expr,
                                     clase=p.TYPEID, nombre_metodo=p.OBJECTID,
                                     argumentos=[])

    @_('expr "@" TYPEID "." OBJECTID "(" args ")"')
    def expr(self, p):
        return LlamadaMetodoEstatico(linea=p.lineno, cuerpo=p.expr,
                                     clase=p.TYPEID, nombre_metodo=p.OBJECTID,
                                     argumentos=p.args)

    # --- Dispatch dinamico: expr.OBJECTID(...) ---
    @_('expr "." OBJECTID "(" ")"')
    def expr(self, p):
        return LlamadaMetodo(linea=p.lineno, cuerpo=p.expr,
                             nombre_metodo=p.OBJECTID, argumentos=[])

    @_('expr "." OBJECTID "(" args ")"')
    def expr(self, p):
        return LlamadaMetodo(linea=p.lineno, cuerpo=p.expr,
                             nombre_metodo=p.OBJECTID, argumentos=p.args)

    # --- Llamada a metodo sobre self: OBJECTID(...) ---
    @_('OBJECTID "(" ")"')
    def expr(self, p):
        return LlamadaMetodo(linea=p.lineno,
                             cuerpo=Objeto(linea=p.lineno, nombre='self'),
                             nombre_metodo=p.OBJECTID, argumentos=[])

    @_('OBJECTID "(" args ")"')
    def expr(self, p):
        return LlamadaMetodo(linea=p.lineno,
                             cuerpo=Objeto(linea=p.lineno, nombre='self'),
                             nombre_metodo=p.OBJECTID, argumentos=p.args)

    # --- IF expr THEN expr ELSE expr FI ---
    @_('IF expr THEN expr ELSE expr FI')
    def expr(self, p):
        return Condicional(linea=p.lineno,
                           condicion=p.expr0, verdadero=p.expr1, falso=p.expr2)

    # --- WHILE expr LOOP expr POOL ---
    @_('WHILE expr LOOP expr POOL')
    def expr(self, p):
        return Bucle(linea=p.lineno, condicion=p.expr0, cuerpo=p.expr1)

    # --- LET bindings IN expr  (bindings multiples -> Let anidados) ---
    @_('LET let_lista IN expr')
    def expr(self, p):
        resultado = p.expr
        for nombre, tipo, init, lineno in reversed(p.let_lista):
            resultado = Let(linea=lineno, nombre=nombre, tipo=tipo,
                            inicializacion=init, cuerpo=resultado)
        return resultado

    @_('let_lista "," let_binding')
    def let_lista(self, p):
        return p.let_lista + [p.let_binding]

    @_('let_binding')
    def let_lista(self, p):
        return [p.let_binding]

    @_('OBJECTID ":" TYPEID')
    def let_binding(self, p):
        return (p.OBJECTID, p.TYPEID, NoExpr(linea=p.lineno), p.lineno)

    @_('OBJECTID ":" TYPEID ASSIGN expr')
    def let_binding(self, p):
        return (p.OBJECTID, p.TYPEID, p.expr, p.lineno)

    @_('OBJECTID ":" TYPEID ASSIGN error')
    def let_binding(self, p):
        return (p.OBJECTID, p.TYPEID, NoExpr(linea=p.lineno), p.lineno)

    # --- CASE expr OF ramas ESAC ---
    @_('CASE expr OF ramas ESAC')
    def expr(self, p):
        obj = Switch(linea=p.lineno, expr=p.expr, casos=p.ramas)
        obj.cast = '_no_type'
        return obj

    @_('case_sin_expr ramas ESAC')
    def expr(self, p):
        if self.errores and 'syntax error at or near DARROW' in self.errores[-1]:
            self.errores.append(
                f'"{self.nombre_fichero}", line {p._slice[2].lineno}: '
                'syntax error at or near ESAC'
            )
        obj = Switch(linea=p.case_sin_expr, expr=NoExpr(linea=p.case_sin_expr),
                     casos=p.ramas)
        obj.cast = '_no_type'
        return obj

    @_('CASE OF')
    def case_sin_expr(self, p):
        self.errores.append(
            f'"{self.nombre_fichero}", line {p.lineno - 1}: '
            'syntax error at or near OF'
        )
        return p.lineno

    @_('ramas rama')
    def ramas(self, p):
        return p.ramas + [p.rama]

    @_('rama')
    def ramas(self, p):
        return [p.rama]

    @_('OBJECTID ":" TYPEID DARROW expr ";"')
    def rama(self, p):
        obj = RamaCase(linea=p.lineno, nombre_variable=p.OBJECTID,
                       tipo=p.TYPEID, cuerpo=p.expr)
        obj.cast = '_no_type'
        return obj

    @_('OBJECTID DARROW expr')
    def rama(self, p):
        self.errores.append(
            f'"{self.nombre_fichero}", line {p.lineno}: '
            'syntax error at or near DARROW'
        )
        obj = RamaCase(linea=p.lineno, nombre_variable=p.OBJECTID,
                       tipo='_no_type', cuerpo=p.expr)
        obj.cast = '_no_type'
        return obj

    @_('error ";"')
    def rama(self, p):
        obj = RamaCase(linea=p.lineno, nombre_variable='_no_set',
                       tipo='_no_type', cuerpo=NoExpr(linea=p.lineno))
        obj.cast = '_no_type'
        return obj

    # --- NEW TYPEID ---
    @_('NEW TYPEID')
    def expr(self, p):
        obj = Nueva(linea=p.lineno, tipo=p.TYPEID)
        obj.cast = '_no_type'
        return obj

    # --- Bloque: { expr; expr; ... } ---
    @_('"{" bloque_exprs "}"')
    def expr(self, p):
        return Bloque(linea=p._slice[2].lineno, expresiones=p.bloque_exprs)

    @_('bloque_exprs expr ";"')
    def bloque_exprs(self, p):
        return p.bloque_exprs + [p.expr]

    @_('bloque_exprs error ";"')
    def bloque_exprs(self, p):
        return p.bloque_exprs

    @_('expr ";"')
    def bloque_exprs(self, p):
        return [p.expr]

    @_('error ";"')
    def bloque_exprs(self, p):
        return []

    # --- Atomos ---
    @_('OBJECTID')
    def expr(self, p):
        return Objeto(linea=p.lineno, nombre=p.OBJECTID)

    @_('INT_CONST')
    def expr(self, p):
        return Entero(linea=p.lineno, valor=int(p.INT_CONST))

    @_('STR_CONST')
    def expr(self, p):
        return String(linea=p.lineno, valor=p.STR_CONST)

    @_('BOOL_CONST')
    def expr(self, p):
        return Booleano(linea=p.lineno, valor=p.BOOL_CONST)

    # ==================================================================
    # Lista de argumentos en llamadas: expr (, expr)*
    # ==================================================================

    @_('args "," expr')
    def args(self, p):
        return p.args + [p.expr]

    @_('expr')
    def args(self, p):
        return [p.expr]

    # ==================================================================
    # Manejo de errores sintacticos
    # ==================================================================

    def error(self, p):
        if p:
            tipo = p.type
            if len(tipo) == 1:
                near = f"'{tipo}'"
            elif tipo in ('TYPEID', 'OBJECTID', 'INT_CONST', 'STR_CONST', 'BOOL_CONST', 'ERROR'):
                near = f'{tipo} = {p.value}'
            else:
                near = tipo
            self.errores.append(
                f'"{self.nombre_fichero}", line {p.lineno}: '
                f'syntax error at or near {near}'
            )
        else:
            self.errores.append(
                f'"{self.nombre_fichero}", line 0: syntax error at or near EOF'
            )
