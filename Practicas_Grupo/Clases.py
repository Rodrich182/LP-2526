# coding: utf-8
from dataclasses import dataclass, field
from typing import List


@dataclass
class Nodo:
    linea: int = 0

    def str(self, n):
        return f'{n*" "}#{self.linea}\n'


@dataclass
class Formal(Nodo):
    nombre_variable: str = '_no_set'
    tipo: str = '_no_type'
    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_formal\n'
        resultado += f'{(n+2)*" "}{self.nombre_variable}\n'
        resultado += f'{(n+2)*" "}{self.tipo}\n'
        return resultado
    def Tipo(self, ambito):
        if self.nombre_variable == 'self':
            ambito.error("'self' cannot be the name of a formal parameter.", self.linea)
        if self.tipo == 'SELF_TYPE':
            ambito.error(f'Formal parameter {self.nombre_variable} cannot have type SELF_TYPE.', self.linea)


class Expresion(Nodo):
    cast: str = '_no_type'
    def Tipo(self, ambito):
        pass


@dataclass
class Asignacion(Expresion):
    nombre: str = '_no_set'
    cuerpo: Expresion = None

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_assign\n'
        resultado += f'{(n+2)*" "}{self.nombre}\n'
        resultado += self.cuerpo.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        if self.nombre == 'self':
            ambito.error("Cannot assign to 'self'.", self.linea)
            self.cast = 'SELF_TYPE'
            return
        self.cuerpo.Tipo(ambito)
        self.cast = self.cuerpo.cast
        declared = ambito.dame_tipo_variable(self.nombre)
        if declared is None:
            ambito.error(f'Undeclared identifier {self.nombre}.', self.linea)
            self.cast = '_no_type'
            return
        if declared != '_no_type' and self.cast != '_no_type':
            if not ambito.es_subtipo(self.cast, declared):
                ambito.error(
                    f'Type {self.cast} of assigned expression does not conform to declared type {declared} of identifier {self.nombre}.',
                    self.linea)


@dataclass
class LlamadaMetodoEstatico(Expresion):
    cuerpo: Expresion = None
    clase: str = '_no_type'
    nombre_metodo: str = '_no_set'
    argumentos: List[Expresion] = field(default_factory=list)

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_static_dispatch\n'
        resultado += self.cuerpo.str(n+2)
        resultado += f'{(n+2)*" "}{self.clase}\n'
        resultado += f'{(n+2)*" "}{self.nombre_metodo}\n'
        resultado += f'{(n+2)*" "}(\n'
        resultado += ''.join([c.str(n+2) for c in self.argumentos])
        resultado += f'{(n+2)*" "})\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.cuerpo.Tipo(ambito)
        for a in self.argumentos:
            a.Tipo(ambito)
        tipo_receptor = self.cuerpo.cast
        if not ambito.es_subtipo(tipo_receptor, self.clase):
            ambito.error(
                f'Expression type {tipo_receptor} does not conform to declared static dispatch type {self.clase}.',
                self.linea)
            self.cast = 'Object'
            return
        metodo = ambito.dame_tipo_metodo(self.clase, self.nombre_metodo)
        if metodo is None:
            ambito.error(f'Dispatch to undefined method {self.nombre_metodo}.', self.linea)
            self.cast = 'Object'
            return
        if len(self.argumentos) == len(metodo['params']):
            for arg, (pname, ptype) in zip(self.argumentos, metodo['params']):
                if not ambito.es_subtipo(arg.cast, ptype):
                    ambito.error(
                        f'In call of method {self.nombre_metodo}, type {arg.cast} of parameter {pname} does not conform to declared type {ptype}.',
                        self.linea)
        self.cast = ambito.resolver_self_type(metodo['retorno'], tipo_receptor)


@dataclass
class LlamadaMetodo(Expresion):
    cuerpo: Expresion = None
    nombre_metodo: str = '_no_set'
    argumentos: List[Expresion] = field(default_factory=list)

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_dispatch\n'
        resultado += self.cuerpo.str(n+2)
        resultado += f'{(n+2)*" "}{self.nombre_metodo}\n'
        resultado += f'{(n+2)*" "}(\n'
        resultado += ''.join([c.str(n+2) for c in self.argumentos])
        resultado += f'{(n+2)*" "})\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.cuerpo.Tipo(ambito)
        for a in self.argumentos:
            a.Tipo(ambito)
        tipo_receptor = self.cuerpo.cast
        clase_lookup = ambito.clase_actual if tipo_receptor == 'SELF_TYPE' else tipo_receptor
        metodo = ambito.dame_tipo_metodo(clase_lookup, self.nombre_metodo)
        if metodo is None:
            ambito.error(f'Dispatch to undefined method {self.nombre_metodo}.', self.linea)
            self.cast = 'Object'
            return
        if len(self.argumentos) == len(metodo['params']):
            for arg, (pname, ptype) in zip(self.argumentos, metodo['params']):
                if not ambito.es_subtipo(arg.cast, ptype):
                    ambito.error(
                        f'In call of method {self.nombre_metodo}, type {arg.cast} of parameter {pname} does not conform to declared type {ptype}.',
                        self.linea)
        self.cast = ambito.resolver_self_type(metodo['retorno'], tipo_receptor)

@dataclass
class Condicional(Expresion):
    condicion: Expresion = None
    verdadero: Expresion = None
    falso: Expresion = None

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_cond\n'
        resultado += self.condicion.str(n+2)
        resultado += self.verdadero.str(n+2)
        resultado += self.falso.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.condicion.Tipo(ambito)
        self.verdadero.Tipo(ambito)
        self.falso.Tipo(ambito)
        self.cast = ambito.mca(self.verdadero.cast, self.falso.cast)


@dataclass
class Bucle(Expresion):
    condicion: Expresion = None
    cuerpo: Expresion = None

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_loop\n'
        resultado += self.condicion.str(n+2)
        resultado += self.cuerpo.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.condicion.Tipo(ambito)
        if self.condicion.cast not in ('Bool', '_no_type'):
            ambito.error('Loop condition does not have type Bool.', self.linea)
        self.cuerpo.Tipo(ambito)
        self.cast = 'Object'


@dataclass
class Let(Expresion):
    nombre: str = '_no_set'
    tipo: str = '_no_set'
    inicializacion: Expresion = None
    cuerpo: Expresion = None

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_let\n'
        resultado += f'{(n+2)*" "}{self.nombre}\n'
        resultado += f'{(n+2)*" "}{self.tipo}\n'
        resultado += self.inicializacion.str(n+2)
        resultado += self.cuerpo.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        if self.nombre == 'self':
            ambito.error("'self' cannot be bound in a 'let' expression.", self.linea)
        self.inicializacion.Tipo(ambito)
        init_cast = self.inicializacion.cast
        if init_cast != '_no_type' and self.tipo != '_no_type':
            if not ambito.es_subtipo(init_cast, self.tipo):
                ambito.error(
                    f'Inferred type {init_cast} of initialization of {self.nombre} does not conform to identifier\'s declared type {self.tipo}.',
                    self.linea + 1)
        ambito.entrar_ambito()
        ambito.definir_variable(self.nombre, self.tipo)
        self.cuerpo.Tipo(ambito)
        self.cast = self.cuerpo.cast
        ambito.salir_ambito()


@dataclass
class Bloque(Expresion):
    expresiones: List[Expresion] = field(default_factory=list)

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{n*" "}_block\n'
        resultado += ''.join([e.str(n+2) for e in self.expresiones])
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        for e in self.expresiones:
            e.Tipo(ambito)
        if self.expresiones:
            self.cast = self.expresiones[-1].cast


@dataclass
class RamaCase(Nodo):
    nombre_variable: str = '_no_set'
    tipo: str = '_no_set'
    cuerpo: Expresion = None

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_branch\n'
        resultado += f'{(n+2)*" "}{self.nombre_variable}\n'
        resultado += f'{(n+2)*" "}{self.tipo}\n'
        resultado += self.cuerpo.str(n+2)
        return resultado
    def Tipo(self, ambito):
        ambito.entrar_ambito()
        ambito.definir_variable(self.nombre_variable, self.tipo)
        self.cuerpo.Tipo(ambito)
        ambito.salir_ambito()


@dataclass
class Switch(Nodo):
    expr: Expresion = None
    casos: List[RamaCase] = field(default_factory=list)
    cast: str = '_no_type'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_typcase\n'
        resultado += self.expr.str(n+2)
        resultado += ''.join([c.str(n+2) for c in self.casos])
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.expr.Tipo(ambito)
        seen_types = set()
        for c in self.casos:
            if c.tipo in seen_types:
                ambito.error(f'Duplicate branch {c.tipo} in case statement.', c.linea)
            seen_types.add(c.tipo)
            c.Tipo(ambito)
        if self.casos:
            result = self.casos[0].cuerpo.cast
            for c in self.casos[1:]:
                result = ambito.mca(result, c.cuerpo.cast)
            self.cast = result
        else:
            self.cast = 'Object'

@dataclass
class Nueva(Nodo):
    tipo: str = '_no_set'
    cast: str = '_no_type'
    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_new\n'
        resultado += f'{(n+2)*" "}{self.tipo}\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        if self.tipo != 'SELF_TYPE' and self.tipo not in ambito.clases:
            ambito.error(f"'new' used with undefined class {self.tipo}.", self.linea)
        self.cast = self.tipo



@dataclass
class OperacionBinaria(Expresion):
    izquierda: Expresion = None
    derecha: Expresion = None


@dataclass
class Suma(OperacionBinaria):
    operando: str = '+'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_plus\n'
        resultado += self.izquierda.str(n+2)
        resultado += self.derecha.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.izquierda.Tipo(ambito)
        self.derecha.Tipo(ambito)
        tl = self.izquierda.cast
        tr = self.derecha.cast
        if tl != '_no_type' and tr != '_no_type' and (tl != 'Int' or tr != 'Int'):
            ambito.error(f'non-Int arguments: {tl} + {tr}', self.linea)
        self.cast = 'Int'


@dataclass
class Resta(OperacionBinaria):
    operando: str = '-'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_sub\n'
        resultado += self.izquierda.str(n+2)
        resultado += self.derecha.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.izquierda.Tipo(ambito)
        self.derecha.Tipo(ambito)
        tl = self.izquierda.cast
        tr = self.derecha.cast
        if tl != '_no_type' and tr != '_no_type' and (tl != 'Int' or tr != 'Int'):
            ambito.error(f'non-Int arguments: {tl} - {tr}', self.linea)
        self.cast = 'Int'


@dataclass
class Multiplicacion(OperacionBinaria):
    operando: str = '*'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_mul\n'
        resultado += self.izquierda.str(n+2)
        resultado += self.derecha.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.izquierda.Tipo(ambito)
        self.derecha.Tipo(ambito)
        tl = self.izquierda.cast
        tr = self.derecha.cast
        if tl != '_no_type' and tr != '_no_type' and (tl != 'Int' or tr != 'Int'):
            ambito.error(f'non-Int arguments: {tl} * {tr}', self.linea)
        self.cast = 'Int'



@dataclass
class Division(OperacionBinaria):
    operando: str = '/'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_divide\n'
        resultado += self.izquierda.str(n+2)
        resultado += self.derecha.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.izquierda.Tipo(ambito)
        self.derecha.Tipo(ambito)
        tl = self.izquierda.cast
        tr = self.derecha.cast
        if tl != '_no_type' and tr != '_no_type' and (tl != 'Int' or tr != 'Int'):
            ambito.error(f'non-Int arguments: {tl} / {tr}', self.linea)
        self.cast = 'Int'


@dataclass
class Menor(OperacionBinaria):
    operando: str = '<'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_lt\n'
        resultado += self.izquierda.str(n+2)
        resultado += self.derecha.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.izquierda.Tipo(ambito)
        self.derecha.Tipo(ambito)
        self.cast = 'Bool'

@dataclass
class LeIgual(OperacionBinaria):
    operando: str = '<='

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_leq\n'
        resultado += self.izquierda.str(n+2)
        resultado += self.derecha.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.izquierda.Tipo(ambito)
        self.derecha.Tipo(ambito)
        self.cast = 'Bool'


@dataclass
class Igual(OperacionBinaria):
    operando: str = '='

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_eq\n'
        resultado += self.izquierda.str(n+2)
        resultado += self.derecha.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.izquierda.Tipo(ambito)
        self.derecha.Tipo(ambito)
        tl = self.izquierda.cast
        tr = self.derecha.cast
        basic = {'Int', 'String', 'Bool'}
        if tl != '_no_type' and tr != '_no_type':
            if (tl in basic or tr in basic) and tl != tr:
                ambito.error('Illegal comparison with a basic type.', self.linea)
        self.cast = 'Bool'

@dataclass
class Neg(Expresion):
    expr: Expresion = None
    operador: str = '~'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_neg\n'
        resultado += self.expr.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.expr.Tipo(ambito)
        self.cast = 'Int'



@dataclass
class Not(Expresion):
    expr: Expresion = None
    operador: str = 'NOT'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_comp\n'
        resultado += self.expr.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.expr.Tipo(ambito)
        self.cast = 'Bool'


@dataclass
class EsNulo(Expresion):
    expr: Expresion = None

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_isvoid\n'
        resultado += self.expr.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.expr.Tipo(ambito)
        self.cast = 'Bool'




@dataclass
class Objeto(Expresion):
    nombre: str = '_no_set'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_object\n'
        resultado += f'{(n+2)*" "}{self.nombre}\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        if self.nombre == 'self':
            self.cast = 'SELF_TYPE'
            return
        self.cast = ambito.dame_tipo_variable(self.nombre)
        if self.cast is None:
            ambito.error(f'Undeclared identifier {self.nombre}.', self.linea)
            self.cast = '_no_type'

@dataclass
class NoExpr(Expresion):
    nombre: str = ''

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_no_expr\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        pass


@dataclass
class Entero(Expresion):
    valor: int = 0

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_int\n'
        resultado += f'{(n+2)*" "}{self.valor}\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.cast = 'Int'

@dataclass
class String(Expresion):
    valor: str = '_no_set'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_string\n'
        resultado += f'{(n+2)*" "}{self.valor}\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.cast = 'String'
    


@dataclass
class Booleano(Expresion):
    valor: bool = False

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_bool\n'
        resultado += f'{(n+2)*" "}{1 if self.valor else 0}\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado
    def Tipo(self, ambito):
        self.cast = 'Bool'

@dataclass
class IterableNodo(Nodo):
    secuencia: List = field(default_factory=list)

@dataclass
class Programa(IterableNodo):
    def str(self, n):
        resultado = super().str(n)
        resultado += f'{" "*n}_program\n'
        resultado += ''.join([c.str(n+2) for c in self.secuencia])
        return resultado

    def Tipo(self):
        ambito = Ambito()
        # Primera pasada: registrar todas las clases
        for c in self.secuencia:
            ambito.registrar_clase(c)
        # Verificaciones globales (herencia, Main)
        ambito.tipo_programa(self)
        # Segunda pasada: analizar cuerpos de clases
        for c in self.secuencia:
            if c.nombre not in ambito.errores_clase_invalida():
                c.Tipo(ambito)
        self.errores_semanticos = ambito.errores

@dataclass
class Caracteristica(Nodo):
    nombre: str = '_no_set'
    tipo: str = '_no_set'
    cuerpo: Expresion = None


@dataclass
class Clase(Nodo):
    nombre: str = '_no_set'
    padre: str = '_no_set'
    nombre_fichero: str = '_no_set'
    caracteristicas: List[Caracteristica] = field(default_factory=list)

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_class\n'
        resultado += f'{(n+2)*" "}{self.nombre}\n'
        resultado += f'{(n+2)*" "}{self.padre}\n'
        resultado += f'{(n+2)*" "}"{self.nombre_fichero}"\n'
        resultado += f'{(n+2)*" "}(\n'
        resultado += ''.join([c.str(n+2) for c in self.caracteristicas])
        resultado += '\n'
        resultado += f'{(n+2)*" "})\n'
        return resultado
    def Tipo(self, ambito):
        ambito.clase_actual = self.nombre
        ambito.fichero_actual = self.nombre_fichero
        ambito.pila_ambito = [{}]
        # Cargar atributos propios e heredados en el ámbito base
        ambito.definir_atributos_clase(self.nombre)
        for c in self.caracteristicas:
            c.Tipo(ambito)

@dataclass
class Metodo(Caracteristica):
    formales: List[Formal] = field(default_factory=list)

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_method\n'
        resultado += f'{(n+2)*" "}{self.nombre}\n'
        resultado += ''.join([c.str(n+2) for c in self.formales])
        resultado += f'{(n + 2) * " "}{self.tipo}\n'
        resultado += self.cuerpo.str(n+2)

        return resultado
    def Tipo(self, ambito):
        # Verificar redefinición de método en clase padre
        metodo_padre = ambito.dame_tipo_metodo_en_padres(ambito.clase_actual, self.nombre)
        if metodo_padre is not None:
            params_padre = metodo_padre['params']
            params_hijo  = [(f.nombre_variable, f.tipo) for f in self.formales]
            if len(params_padre) != len(params_hijo):
                ambito.error(
                    f'Incompatible number of formal parameters in redefined method {self.nombre}.',
                    self.linea)
            else:
                for (pn_p, pt_p), (pn_h, pt_h) in zip(params_padre, params_hijo):
                    if pt_p != pt_h:
                        ambito.error(
                            f'In redefined method {self.nombre}, parameter type {pt_h} is different from original type {pt_p}',
                            self.linea)
        # Verificar formales
        vistos = set()
        ambito.entrar_ambito()
        for f in self.formales:
            f.Tipo(ambito)
            if f.nombre_variable in vistos:
                ambito.error(f'Formal parameter {f.nombre_variable} is multiply defined.', self.linea)
            vistos.add(f.nombre_variable)
            ambito.definir_variable(f.nombre_variable, f.tipo)
        # Verificar tipo retorno existe
        if self.tipo != 'SELF_TYPE' and self.tipo not in ambito.clases:
            ambito.error(f'Undefined return type {self.tipo} in method {self.nombre}.', self.linea)
        self.cuerpo.Tipo(ambito)
        ambito.salir_ambito()
        # Verificar tipo retorno del cuerpo
        tipo_cuerpo = self.cuerpo.cast
        if tipo_cuerpo != '_no_type' and self.tipo != '_no_type':
            if self.tipo == 'SELF_TYPE' and tipo_cuerpo != 'SELF_TYPE':
                ambito.error(
                    f'Inferred return type {tipo_cuerpo} of method {self.nombre} does not conform to declared return type {self.tipo}.',
                    self.linea)
            elif not ambito.es_subtipo(tipo_cuerpo, self.tipo):
                ambito.error(
                    f'Inferred return type {tipo_cuerpo} of method {self.nombre} does not conform to declared return type {self.tipo}.',
                    self.linea)


class Atributo(Caracteristica):

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_attr\n'
        resultado += f'{(n+2)*" "}{self.nombre}\n'
        resultado += f'{(n+2)*" "}{self.tipo}\n'
        resultado += self.cuerpo.str(n+2)
        return resultado
    def Tipo(self, ambito):
        if self.nombre == 'self':
            ambito.error("'self' cannot be the name of an attribute.", self.linea)
        if ambito.attr_en_herencia(ambito.clase_actual, self.nombre):
            ambito.error(f'Attribute {self.nombre} is an attribute of an inherited class.', self.linea)
        self.cuerpo.Tipo(ambito)
        init_cast = self.cuerpo.cast
        if init_cast != '_no_type' and self.tipo != '_no_type':
            if not ambito.es_subtipo(init_cast, self.tipo):
                ambito.error(
                    f'Inferred type {init_cast} of initialization of {self.nombre} does not conform to identifier\'s declared type {self.tipo}.',
                    self.linea)
