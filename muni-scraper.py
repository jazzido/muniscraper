# coding: utf-8
import sys, urlparse, cStringIO, codecs, unicodecsv

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

def get_munis_by_prov(prov_code):
    """ genera lista de codigos de municipios segun `prov_code` """
    url = 'http://www.mininterior.gov.ar/municipios/lista_municipios.php?provincia=%s' % prov_code
    print >>sys.stderr, "requesting: %s" % url
    r = requests.get(url)
    for opt in html.document_fromstring(r.text).cssselect('option'):
        if opt.attrib.get('value', '') != '':
            yield opt.attrib['value'], opt.text

def get_muni_data(code):
    """ scrapea datos de municipio, retorna dict """
    url = 'http://www.mininterior.gov.ar/municipios/masinfo.php?municipio=%s' % code
    print >>sys.stderr, "requesting url: %s" % url
    r = requests.get(url)

    if 'mal formado' in r.text:
        return None

    doc = html.document_fromstring(r.text.encode('iso-8859-1'))

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
    rv = {}
    if len(trs) > 1:
        for tr in element.cssselect('tr'):
            k = key_prefix + ' ' + tr.cssselect('td')[0].text_content().strip()
            td = tr.cssselect('td')[1]
            etree.strip_tags(td, 'a', 'strong', 'p')
            rv[k] = ','.join(td.itertext())
    return rv

def main():
    csv_writer = unicodecsv.DictWriter(sys.stdout, FIELDS)
    csv_writer.writeheader()
    for prov_code in sorted(PROVINCIAS.keys()):
        for muni_code, _ in get_munis_by_prov(prov_code):
            print >>sys.stderr, '---'
            print >>sys.stderr, "PARSING MUNI: %s" % muni_code
            try:
                row = get_muni_data(muni_code)
                if row is None:
                    continue
                print >>sys.stderr,row
                csv_writer.writerow(row)
                print >>sys.stderr,'---'
            except:
                print >>sys.stderr, 'Error en fuente'
                print >>sys.stderr,'---'
                continue


if __name__ == '__main__':
    main()
