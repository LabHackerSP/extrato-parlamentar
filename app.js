var request = require("request-promise-native");
var moment = require("moment");
var express = require("express");
var app = express();

const PORT = 8008;

function requestLog(req) {
  try {
    console.log(`[${moment().format("DD/MM/YYYY HH:mm")}] ${req.ip} ${req.method} ${req.originalUrl}`);
  } catch(e) {}
}

async function getTramitacoes() {
  let urlLista = "https://dadosabertos.camara.leg.br/api/v2/proposicoes?siglaTipo=PL&siglaTipo=PLS&siglaTipo=PEC&itens=100&dataInicio=" + moment().format("YYYY-MM-DD");

  let tramita = await request({
    method: 'GET',
    uri: urlLista,
    json: true
  });

  try{
    for(let p in tramita.dados) {
      let urlDetalhe = tramita.dados[p].uri;
      let detalhe = await request({
        method: 'GET',
        uri: urlDetalhe,
        json: true
      });
      tramita.dados[p] = detalhe.dados;

      let urlAutores = tramita.dados[p].uriAutores;
      let autores = await request({
        method: 'GET',
        uri: urlAutores,
        json: true
      });
      tramita.dados[p].autores = {};
      for(let a in autores.dados) {
        let urlAutor = autores.dados[a].uri;
        let autor = await request({
          method: 'GET',
          uri: urlAutor,
          json: true
        });
        tramita.dados[p].autores[autores.dados[a].id] = autor.dados;
      }
    }
  } catch(e) {
    console.log(e.stack);
    return false;
  }

  return tramita.dados;
}

const ESC       = "\x1b"
const GS        = "\x1d"
const BOLD      = ESC + "\x45" // 0 or 1
const UNDERLINE = ESC + "\x2d" // 0 or 1
const REVERSE   = GS  + "\x42" // 0 or 1
const JUSTIFY   = ESC + "\x61" // 0 = l, 1 = c, 2 = r
const FONT      = ESC + "\x4d" // 0 = a, 1 = b
const SIZE      = GS  + "\x21" // 10 = dh, 01 = dw
const CODEPAGE   = ESC + "\x74" // 0 = CP437, 6 = WS1252

async function makeExtrato(tramita) {
  let output = "";

  // tweak heating time
  // n1 = printing dots / 8dots
  // n2 = heating time / 10us
  // n3 = heating interval / 10us
  output += ESC + "\x37\x07\x7f\x02";

  // header
  output += BOLD+"\x01";
  output += JUSTIFY+"\x01";
  output += "################################\n";
  output += SIZE+"\x11";
  output += "Extrato\nParlamentar\n";
  output += SIZE+"\x00";
  output += "################################\n";
  output += JUSTIFY+"\x00";
  output += BOLD+"\x00";

  // TODO: não fazer fetch aqui, fazer ao iniciar o servidor e a cada dia
  let t = await getTramitacoes();

  if(!t) {
    output += "Falha ao contatar a API!\n\n\n";
    return output;
  }

  // info
  output += `Alguns projetos de ${moment().format("DD/MM/YYYY")}:\n`;

  // TODO: seleciona 4 projetos e imprime

  p = t[0];

  // titulo
  output += BOLD+"\x01";
  output += JUSTIFY+"\x01";
  output += CODEPAGE+"\x00";
  output += "\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\n";
  output += SIZE+"\x11";
  output += `[${p.siglaTipo} ${p.numero}/${p.ano}]\n`;
  output += SIZE+"\x00";
  output += "\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\xdb\n";
  output += JUSTIFY+"\x00";
  output += BOLD+"\x00";

  // feed
  output += "\n\n\n";

  return output;
}

app.get('/binary', function(req, res) {
  //let binary = fs.readFileSync("testfile");
  res.type('application/octet-stream');
  makeExtrato().then((output) => {
    res.status(200).send(output);
  })
  requestLog(req);
});

app.listen(PORT, '0.0.0.0', () => console.log(`Example app listening on port ${PORT}!`));