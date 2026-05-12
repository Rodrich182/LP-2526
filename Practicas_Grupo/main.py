import os
import re
import sys
# from colorama import init  ## Para colorear la salida en la terminal
# from termcolor import colored ## Para colorear la salida en la terminal
#init()
def colored(text, *args, **kwargs):
    return text


DIRECTORIO = os.path.expanduser("./")
sys.path.append(DIRECTORIO)

from Lexer import *
from Parser import *
import Clases
from Clases import *

class Ambito:
    BUILTINS  = {'Object', 'IO', 'Int', 'String', 'Bool'}
    NO_HEREDA = {'Int', 'String', 'Bool', 'SELF_TYPE'}
    BASIC_TYPES = {'Int', 'Bool', 'String'}

    def __init__(self):
        self.errores = []
        self.clases = {}
        self.pila_ambito = [{}]
        self.clase_actual = None
        self.fichero_actual = None
        self._inicializar_builtins()

    def _inicializar_builtins(self):
        self.clases['Object'] = {
            'padre': None, 'atributos': {},
            'metodos': {
                'abort':     {'params': [],                          'retorno': 'Object'},
                'type_name': {'params': [],                          'retorno': 'String'},
                'copy':      {'params': [],                          'retorno': 'SELF_TYPE'},
            },
        }
        self.clases['IO'] = {
            'padre': 'Object', 'atributos': {},
            'metodos': {
                'out_string': {'params': [('x', 'String')],          'retorno': 'SELF_TYPE'},
                'out_int':    {'params': [('x', 'Int')],             'retorno': 'SELF_TYPE'},
                'in_string':  {'params': [],                          'retorno': 'String'},
                'in_int':     {'params': [],                          'retorno': 'Int'},
            },
        }
        self.clases['Int']  = {'padre': 'Object', 'metodos': {}, 'atributos': {}}
        self.clases['Bool'] = {'padre': 'Object', 'metodos': {}, 'atributos': {}}
        self.clases['String'] = {
            'padre': 'Object', 'atributos': {},
            'metodos': {
                'length': {'params': [],                              'retorno': 'Int'},
                'concat': {'params': [('s', 'String')],              'retorno': 'String'},
                'substr': {'params': [('i', 'Int'), ('l', 'Int')],   'retorno': 'String'},
            },
        }

    # ── errors ──────────────────────────────────────────────────────────────
    def error(self, mensaje, linea=None, fichero=None):
        f = fichero if fichero is not None else (self.fichero_actual or '')
        if linea:
            self.errores.append(f'{f}:{linea}: {mensaje}')
        else:
            self.errores.append(mensaje)

    # ── class registration ──────────────────────────────────────────────────
    def registrar_clase(self, clase):
        nombre = clase.nombre
        if nombre == 'SELF_TYPE' or nombre in self.BUILTINS:
            self.error(f'Redefinition of basic class {nombre}.', clase.linea, clase.nombre_fichero)
            return
        if nombre in self.clases:
            self.error(f'Class {nombre} was previously defined.', clase.linea, clase.nombre_fichero)
            return
        metodos = {}
        atributos = {}
        for c in clase.caracteristicas:
            if isinstance(c, Metodo):
                metodos[c.nombre] = {
                    'params': [(f.nombre_variable, f.tipo) for f in c.formales],
                    'retorno': c.tipo,
                    'linea': c.linea,
                }
            elif isinstance(c, Atributo):
                atributos[c.nombre] = c.tipo
        self.clases[nombre] = {
            'padre':    clase.padre,
            'metodos':  metodos,
            'atributos': atributos,
            'linea':    clase.linea,
            'fichero':  clase.nombre_fichero,
        }

    # ── scope management ────────────────────────────────────────────────────
    def entrar_ambito(self):
        self.pila_ambito.append({})

    def salir_ambito(self):
        if len(self.pila_ambito) > 1:
            self.pila_ambito.pop()

    def definir_variable(self, nombre, tipo):
        self.pila_ambito[-1][nombre] = tipo

    def dame_tipo_variable(self, nombre):
        for scope in reversed(self.pila_ambito):
            if nombre in scope:
                return scope[nombre]
        clase = self.clase_actual
        visitados = set()
        while clase and clase not in visitados:
            visitados.add(clase)
            info = self.clases.get(clase)
            if info is None:
                break
            if nombre in info.get('atributos', {}):
                return info['atributos'][nombre]
            clase = info.get('padre')
        return None

    # ── method lookup ────────────────────────────────────────────────────────
    def dame_tipo_metodo(self, clase_nombre, nombre_metodo):
        clase = self.clase_actual if clase_nombre == 'SELF_TYPE' else clase_nombre
        visitados = set()
        while clase and clase not in visitados:
            visitados.add(clase)
            info = self.clases.get(clase)
            if info is None:
                break
            if nombre_metodo in info.get('metodos', {}):
                return info['metodos'][nombre_metodo]
            clase = info.get('padre')
        return None

    def dame_tipo_metodo_en_padres(self, clase_nombre, nombre_metodo):
        info = self.clases.get(clase_nombre)
        if info is None:
            return None
        return self.dame_tipo_metodo(info.get('padre'), nombre_metodo)

    # ── type relations ───────────────────────────────────────────────────────
    def es_subtipo(self, t1, t2):
        if t1 == t2:
            return True
        if t2 == 'Object':
            return True
        if '_no_type' in (t1, t2):
            return True
        c1 = self.clase_actual if t1 == 'SELF_TYPE' else t1
        c2 = self.clase_actual if t2 == 'SELF_TYPE' else t2
        if c1 == c2:
            return True
        visitados = set()
        c = c1
        while c and c not in visitados:
            visitados.add(c)
            if c == c2:
                return True
            info = self.clases.get(c)
            if info is None:
                break
            c = info.get('padre')
        return False

    def mca(self, t1, t2):
        if t1 == t2:
            return t1
        if t1 == '_no_type':
            return t2
        if t2 == '_no_type':
            return t1
        c1 = self.clase_actual if t1 == 'SELF_TYPE' else t1
        c2 = self.clase_actual if t2 == 'SELF_TYPE' else t2
        anc1 = []
        c, vis = c1, set()
        while c and c not in vis:
            vis.add(c); anc1.append(c)
            info = self.clases.get(c)
            if info is None: break
            c = info.get('padre')
        anc1_set = set(anc1)
        c, vis = c2, set()
        while c and c not in vis:
            vis.add(c)
            if c in anc1_set:
                return c
            info = self.clases.get(c)
            if info is None: break
            c = info.get('padre')
        return 'Object'

    def resolver_self_type(self, tipo_retorno, tipo_receptor):
        if tipo_retorno == 'SELF_TYPE':
            return tipo_receptor
        return tipo_retorno

    # ── attribute inheritance check ──────────────────────────────────────────
    def attr_en_herencia(self, clase_nombre, nombre_attr):
        info = self.clases.get(clase_nombre)
        if info is None:
            return False
        clase = info.get('padre')
        visitados = set()
        while clase and clase not in visitados:
            visitados.add(clase)
            info = self.clases.get(clase)
            if info is None:
                break
            if nombre_attr in info.get('atributos', {}):
                return True
            clase = info.get('padre')
        return False

    # ── invalid class names (had registration errors) ────────────────────────
    def errores_clase_invalida(self):
        """Returns a set of class names that should NOT be analyzed (registration errors)."""
        invalidas = set()
        for e in self.errores:
            # Redefinition or previously defined errors affect the class
            pass
        return invalidas

    # ── load class attributes into current scope ──────────────────────────────
    def definir_atributos_clase(self, clase_nombre):
        """Push all attributes (including inherited) of clase_nombre into current scope."""
        cadena = []
        c = clase_nombre
        visitados = set()
        while c and c not in visitados:
            visitados.add(c)
            info = self.clases.get(c)
            if info is None:
                break
            cadena.append((c, info.get('atributos', {})))
            c = info.get('padre')
        # Define from oldest ancestor down so child overrides parent
        for _, attrs in reversed(cadena):
            for nombre, tipo in attrs.items():
                self.pila_ambito[0][nombre] = tipo

    # ── global program checks ────────────────────────────────────────────────
    def tipo_programa(self, programa):
        if 'Main' not in self.clases:
            self.errores.append('Class Main is not defined.')
        for nombre, info in self.clases.items():
            if nombre in self.BUILTINS:
                continue
            padre = info.get('padre')
            if padre is None:
                continue
            fichero = info.get('fichero', '')
            linea   = info.get('linea', 0)
            if padre in self.NO_HEREDA:
                self.errores.append(f'{fichero}:{linea}: Class {nombre} cannot inherit class {padre}.')
            elif padre not in self.clases:
                self.errores.append(f'{fichero}:{linea}: Class {nombre} inherits from an undefined class {padre}.')

Clases.Ambito = Ambito

PRACTICA = "03" # Practica que hay que evaluar
DEBUG = True   # Decir si se lanzan mensajes de debug
NUMLINEAS = 3   # Numero de lineas que se muestran antes y después de la no coincidencia
sys.path.append(DIRECTORIO)
DIR = os.path.join(DIRECTORIO, PRACTICA, 'grading')
FICHEROS = os.listdir(DIR)
TESTS = [fich for fich in FICHEROS
         if os.path.isfile(os.path.join(DIR, fich)) and
         re.search(r"^[a-zA-Z].*\.(cool|test|cl)$",fich)]
TESTS.sort()
#TESTS = ["escapedunprintables.cool"]

if True:
    for fich in TESTS:
        lexer = CoolLexer()
        f = open(os.path.join(DIR, fich), 'r', newline='')
        g = open(os.path.join(DIR, fich + '.out'), 'r', newline='')
        if os.path.isfile(os.path.join(DIR, fich)+'.nuestro'):
            os.remove(os.path.join(DIR, fich)+'.nuestro')
        if os.path.isfile(os.path.join(DIR, fich)+'.bien'):
            os.remove(os.path.join(DIR, fich)+'.bien')            
        texto = ''
        entrada = f.read()
        f.close()
        if PRACTICA == '01':
            texto = '\n'.join(lexer.salida(entrada))
            texto = f'#name "{fich}"\n' + texto
            resultado = g.read()
            g.close()
            texto = re.sub(r'#\d+\b','',texto)
            resultado = re.sub(r'#\d+\b','',resultado)
            nuestro = [linea.strip() for linea in texto.split('\n') if linea.strip()]
            bien = [linea.strip() for linea in resultado.split('\n') if linea.strip()]
            texto = '\n'.join(nuestro)
            resultado = '\n'.join(bien)
            #print(texto)
            #print(resultado)
            if texto.strip().split() != resultado.strip().split():
                print(f"Revisa el fichero {fich}")
                if DEBUG:
                    f = open(os.path.join(DIR, fich)+'.nuestro', 'w')
                    g = open(os.path.join(DIR, fich)+'.bien', 'w')
                    f.write(texto.strip())
                    g.write(resultado.strip())
                    f.close()
                    g.close()
        elif PRACTICA in ('02', '03'):
            parser = CoolParser()
            parser.nombre_fichero = fich
            parser.errores = []
            bien = ''.join([c for c in g.readlines() if c and '#' not in c])
            bien_total = bien
            g.close()
            j = parser.parse(lexer.tokenize(entrada))
            try:
                if j is not None and PRACTICA == '03':
                    j.Tipo()
                if j is not None and not parser.errores:
                    if PRACTICA == '03' and j.errores_semanticos:
                        resultado = '\n'.join(j.errores_semanticos)
                        resultado += '\n' + 'Compilation halted due to static semantic errors.'
                    else:
                        resultado = '\n'.join([c for c in j.str(0).split('\n')
                                               if c and '#' not in c])
                else:
                    resultado = '\n'.join(parser.errores)
                    resultado += '\n' + "Compilation halted due to lex and parse errors"
                if resultado.lower().strip().split() != bien.lower().strip().split():
                    print(f"Revisa el fichero {fich}")
                    if DEBUG:
                        nuestro = [linea for linea in resultado.split('\n') if linea]
                        bien = [linea for linea in bien.split('\n') if linea]
                        linea = 0
                        while nuestro[linea:linea+NUMLINEAS] == bien[linea:linea+NUMLINEAS]:
                            linea += 1
                        print(colored('\n'.join(nuestro[linea:linea+NUMLINEAS]), 'white', 'on_red'))
                        print(colored('\n'.join(bien[linea:linea+NUMLINEAS]), 'blue', 'on_green'))
                        f = open(os.path.join(DIR, fich)+'.nuestro', 'w')
                        g = open(os.path.join(DIR, fich)+'.bien', 'w')
                        f.write(resultado.strip())
                        g.write(bien_total.strip())
                        f.close()
                        g.close()
            except Exception as e:
                print(f"Lanza excepción en {fich} con el texto {e}")

