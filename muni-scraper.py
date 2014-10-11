# coding: utf-8
import sys, urlparse, csv, cStringIO, codecs

import requests
from lxml import html, etree


PROVINCIAS = {
    'BUE':'Buenos Aires',
    'CAT':'Catamarca',
    'CHA':'Chaco',
    'CHU':'Chubut',
    'CBA':'Córdoba',
    'COR':'Corrientes',
    'ERI':'Entre Ríos',
    'FOR':'Formosa',
    'JUJ':'Jujuy',
    'LAP':'La Pampa',
    'LRJ':'La Rioja',
    'MZA':'Mendoza',
    'MIS':'Misiones',
    'NEU':'Neuquén',
    'RNO':'Río Negro',
    'SAL':'Salta',
    'SJU':'San Juan',
    'SLU':'San Luis',
    'SCR':'Santa Cruz',
    'SFE':'Santa Fe',
    'SGO':'Santiago del Estero',
    'TDF':'Tierra del Fuego',
    'TUC':'Tucumán',
}

FIELDS = [
    'Codigo Municipio',
    'Codigo Provincia',
    'Nombre Municipio',
    'Nombre Provincia',
    'Municipio Lat',
    'Municipio Long',
    u'Datos de Contacto Direcci\xf3n postal',
    'Datos de Contacto E-mail',
    'Datos de Contacto Sitio web',
    u'Datos de Contacto Tel\xe9fonos',
    u'Info Institucional Carta Org\xe1nica',
    u'Info Institucional Categor\xeda',
    u'Info Institucional Fecha de creaci\xf3n',
    'Jefe de Gobierno Cargo',
    'Jefe de Gobierno Nombre y Apellido',
    'Jefe de Gobierno Reelecto'
]

class DictUnicodeWriter(object):

    def __init__(self, f, fieldnames, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.fieldnames = fieldnames
        self.queue = cStringIO.StringIO()
        self.writer = csv.DictWriter(self.queue, fieldnames, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, D):
        self.writer.writerow({k:v.encode("utf-8") for k,v in D.items()})
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for D in rows:
            self.writerow(D)

    def writeheader(self):
        header = dict(zip(self.fieldnames, self.fieldnames))
        self.writerow(header)

def get_munis_by_prov(prov_code):
    """ genera lista de codigos de municipios segun `prov_code` """
    r = requests.get('http://www.mininterior.gov.ar/municipios/lista_municipios.php?provincia=%s' % prov_code)
    for opt in html.document_fromstring(r.text).cssselect('option'):
        if opt.attrib.get('value', '') != '':
            yield opt.attrib['value'], opt.text

def get_muni_data(code):
    """ scrapea datos de municipio, retorna dict """
    r = requests.get('http://www.mininterior.gov.ar/municipios/masinfo.php?municipio=%s' % code)

    if 'mal formado' in r.text:
        return None

    doc = html.document_fromstring(r.text)

    rv = {}

    rv['Nombre Provincia'] = PROVINCIAS[code[:3]].decode('utf-8')
    rv['Codigo Provincia'] = code[:3]
    rv['Codigo Municipio'] = code
    rv['Nombre Municipio'] = doc.cssselect('div#mas-info h1')[0].text_content().strip()
    rv['Municipio Long'], rv['Municipio Lat'] = '', ''

    iframe = doc.cssselect('iframe')
    if len(iframe) > 0:
        rv['Municipio Long'], rv['Municipio Lat'] = urlparse.parse_qs(urlparse.urlparse(iframe[0].attrib['src']).query)['q'][0].split(',')

    # jefe de gobierno
    table = doc.xpath('//h3/strong[contains(., "Jefe")]/../following-sibling::table[1]')[0]
    rv.update(_scrape_table(table, 'Jefe de Gobierno'))

    # informacion institucional
    table = doc.xpath('//h3[contains(., "Institucional")]/following-sibling::table[1]')[0]
    rv.update(_scrape_table(table, 'Info Institucional'))

    # datos de contacto
    table = doc.xpath('//h3[contains(., "DATOS DE")]/following-sibling::table[1]')[0]
    rv.update(_scrape_table(table, 'Datos de Contacto'))

    return rv


def _scrape_table(element, key_prefix=''):
    """ recibe un `Element`, devuelve diccionario """
    trs = element.cssselect('tr')
    if len(trs) > 1:
        return { key_prefix + ' ' + tr.cssselect('td')[0].text_content().strip(): unicode(tr.cssselect('td')[1].text_content().strip())
                 for tr in element.cssselect('tr') }
    else:
        return {}


def main():
    csv_writer = DictUnicodeWriter(sys.stdout, FIELDS)
    csv_writer.writeheader()
    for prov_code in PROVINCIAS.keys():
        for muni_code, _ in get_munis_by_prov(prov_code):
            print >>sys.stderr, '---'
            print >>sys.stderr, "PARSING MUNI: %s" % muni_code
            row = get_muni_data(muni_code)
            if row is None:
                print >>sys.stderr, 'Error en fuente'
                print >>sys.stderr,'---'
                continue
            print >>sys.stderr,row
            csv_writer.writerow(row)
            print >>sys.stderr,'---'

if __name__ == '__main__':
    main()
