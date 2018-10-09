#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json, requests, os, qrcode, sys, struct, math
from datetime import datetime, timedelta
from io import BytesIO
from flask import Flask, render_template, redirect
from werkzeug.wrappers import Request, Response
from PIL import Image, ImageOps

# API - https://dadosabertos.camara.leg.br/swagger/api.html
# PATH = os.path.dirname(os.path.abspath(__file__)) + "/data/archive.json"
HOSTNAME = "https://ep.labhacker.org.br/"

ESC       = b"\x1b"
GS        = b"\x1d"
DC2       = b"\x12"
BOLD      = ESC + b"\x45" # 0 or 1
UNDERLINE = ESC + b"\x2d" # 0 or 1
REVERSE   = GS  + b"\x42" # 0 or 1
JUSTIFY   = ESC + b"\x61" # 0 = l, 1 = c, 2 = r
FONT      = ESC + b"\x4d" # 0 = a, 1 = b
SIZE      = GS  + b"\x21" # 10 = dh, 01 = dw
CODEPAGE  = ESC + b"\x74" # 0 = CP437, 16 = WS1252
CHAR      = ESC + b"\x21" # 0 = font a, 1 = font b

class Tramitacoes():
  def __init__(self, data={}):
    self.url = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
    self.data = data
    self.results = requests.get(self.url, data)
    self.tramitacoes = json.loads(self.results.content.decode("utf-8"))['dados']

  def getDetalhe(self):
    for p in self.tramitacoes:
      r = requests.get(self.url+"/"+str(p['id']))
      p.update(json.loads(r.content.decode("utf-8"))['dados'])

  def getVotacoes(self):
    print("Getting Votacoes...")
    for p in self.tramitacoes:
      r = requests.get(self.url+"/"+str(p['id'])+"/votacoes")
      p['votacao'] = json.loads(r.content.decode("utf-8"))['dados']
      print(p['votacao'])

  def getAutor(self):
    print("Getting autores...")
    for p in self.tramitacoes:
      r = requests.get(self.url+"/"+str(p['id'])+"/autores")
      p['autores'] = json.loads(r.content.decode("utf-8"))['dados']
      for a in p['autores']:
        if a["uri"]:
          r = requests.get(a["uri"])
          a.update(json.loads(r.content.decode("utf-8"))['dados'])

# retorna lista de tramitações do dia
def lockandload(date):
  data = datetime.strftime(date, "%Y-%m-%d")
  path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", data+".json")

  if os.path.isfile(path):
    tt = json.load(open(path, 'r'))
  else:
    query = {
      "siglaTipo": ["PL","PLS","PEC"],
      "dataInicio": data
    }

    t = Tramitacoes(query)
    t.getDetalhe()
    t.getAutor()
    arquivo = open(path, 'w')
    tt = t.tramitacoes
    with open(path, 'w') as arquivo:
      json.dump(tt, arquivo)
  
  return tt

# converte imagem PIL para binário da impressora, retorna com comando de controle inicial
def converteFoto(p, w=None, h=None):
  out = DC2 + b'*'

  pic = p.copy()
  size = (p.width, p.height)
  if w or h:
    if w == None:
      size = (math.ceil(p.width / (p.height / h)), h)
    elif h == None:
      size = (w, math.ceil(p.height / (p.width / w)))
    else:
      size = (w, h)
    # escala
    pic = pic.resize(size)
  
  # converte imagem para p/b
  pic = ImageOps.invert(pic)
  pic = pic.convert("1")

  out += struct.pack("B", size[1])
  out += struct.pack("B", math.floor(size[0]/8))

  out += pic.tobytes()
  return out

# busca foto de político com id e url e retorna binário
def getFoto(id, url):
  path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", str(id)+".pic")
  
  pic = b''

  try:
    # carrega imagem pré-computada
    with open(path, "rb") as f:
      pic = f.read()
  except (IOError, FileNotFoundError):
    r = requests.get(url)
    p = Image.open(BytesIO(r.content))
    #converte para formato da impressora
    pic = converteFoto(p, w=112)
    with open(path, "wb") as f:
      f.write(pic)

  return pic

app = Flask(__name__)

@app.route("/")
def tramita():
  tt = lockandload()
  return render_template('tramita.html', projetos=tt)

# monta a saída binária da impressora térmica
def build_binary(date=datetime.now()):
  line1 = b"################################\n"

  yield ESC + b"\x37\x07\x40\x01"
  yield CODEPAGE + b"\x23"

  yield BOLD+b"\x01"
  yield JUSTIFY+b"\x01"
  yield line1
  yield SIZE+b"\x11"
  yield b"Extrato\nParlamentar\n"
  yield SIZE+b"\x00"
  yield line1
  yield JUSTIFY+b"\x00"
  yield BOLD+b"\x00"

  tt = lockandload(date)

  if not tt:
    yield b"Erro ao ler API!\n"
  else:
    yield b"Projetos de "
    yield datetime.strftime(date, "%Y-%m-%d").encode("ascii")
    yield b"\n"

    for t in tt:
      #titulo (PEC num/ano)
      yield SIZE+b"\x10"
      yield b"[" + t['siglaTipo'].encode("ascii") + b" " + str(t['numero']).encode("ascii") + b"/" + str(t['ano']).encode("ascii") + b"]\n"
      yield SIZE+b"\x00"
      #ementa + ementa detalhada
      yield t['ementa'].encode("cp1252") + b"\n"
      # TODO: quebra de linha sem quebrar palavras
      #status
      yield BOLD+b"\x01"
      yield b"Status: "
      yield BOLD+b"\x00"
      yield t['statusProposicao']['descricaoSituacao'].encode("cp1252") + b"\n"
      #autor
      # TODO: foto
      for a in t['autores']:
        try:
          if a['ultimoStatus']:
            if a['ultimoStatus']['urlFoto']:
              yield getFoto(a['id'], a['ultimoStatus']['urlFoto'])
            yield a['ultimoStatus']['nome'].encode("cp1252")
            yield b" - "
            yield a['ultimoStatus']['siglaPartido'].encode("ascii")
        except KeyError:
          print(a)
          yield a['nome'].encode("cp1252")
          pass
        yield b"\n"
      #url
      # TODO: qrcode
      yield CHAR + b"\x01"
      yield b"URL: " + HOSTNAME.encode("ascii")
      yield str(t['id']).encode("ascii")
      yield CHAR + b"\x00"
      yield b"\n"
      yield line1

  yield b"\n\n\n"

@app.route("/binary")
def binary():
  return Response(build_binary(), mimetype='application/octet-stream')

@app.route("/binary2")
def binary2():
  return Response(build_binary(datetime.now() - timedelta(1)), mimetype='application/octet-stream')

@app.route("/s/<id>")
def shorten(id):
  if(not id.isdigit()):
    raise ValueError("ID só pode conter números")
  return redirect("http://www.camara.gov.br/proposicoesWeb/fichadetramitacao?idProposicao="+id)