import json, requests, os
from datetime import datetime
from flask import Flask, render_template
from werkzeug.wrappers import Request, Response

# API - https://dadosabertos.camara.leg.br/swagger/api.html
# PATH = os.path.dirname(os.path.abspath(__file__)) + "/data/archive.json"

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

def lockandload():
  data = datetime.strftime(datetime.now(), "%Y-%m-%d")
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

app = Flask(__name__)

@app.route("/")
def tramita():
  tt = lockandload()
  return render_template('tramita.html', projetos=tt)

@app.route("/binary")
def binary():
  tt = lockandload()

  ESC       = b"\x1b"
  GS        = b"\x1d"
  BOLD      = ESC + b"\x45" # 0 or 1
  UNDERLINE = ESC + b"\x2d" # 0 or 1
  REVERSE   = GS  + b"\x42" # 0 or 1
  JUSTIFY   = ESC + b"\x61" # 0 = l, 1 = c, 2 = r
  FONT      = ESC + b"\x4d" # 0 = a, 1 = b
  SIZE      = GS  + b"\x21" # 10 = dh, 01 = dw
  CODEPAGE  = ESC + b"\x74" # 0 = CP437, 6 = WS1252

  output = b""

  output += ESC + b"\x37\x07\x7f\x02"

  output += BOLD+b"\x01"
  output += JUSTIFY+b"\x01"
  output += b"################################\n"
  output += SIZE+b"\x11"
  output += b"Extrato\nParlamentar\n"
  output += SIZE+b"\x00"
  output += b"################################\n"
  output += JUSTIFY+b"\x00"
  output += BOLD+b"\x00"

  output += b"Projetos de "
  output += datetime.strftime(datetime.now(), "%Y-%m-%d").encode("ascii")
  output += b"\n"

  return Response(output, mimetype='application/octet-stream')