#!/usr/bin/env python3

# Imports
import sys
from textwrap import wrap as _wrap
import xml.etree.ElementTree as ET # Parse XML
import sqlite3 # Database Interface
from pathlib import Path

def wrap(*args, **kw):
    '''Wrapper function for textwrap.wrap that joins the lines with newlines
    '''
    return '\n'.join(_wrap(*args, **kw))

# Default XML file
UCD_FILE = 'ucd.all.grouped.xml'
# XML Namespace
UCD_XMLNS = 'http://www.unicode.org/ns/2003/ucd/1.0'

# Output database
DB_FILE = 'db'

class Db:
    '''Database Wrapper class for sqlite3'''

    def __init__(self, path):
        self.path = path

    def count(self):
        self.db.execute('SELECT COUNT(*) FROM symbols')
        self.n = self.db.fetchall()[0][0]

    def connect(self):
        self.db_connection = sqlite3.connect(str(self.path))
        self.db = self.db_connection.cursor()
    
    def create(self):
        self.n = 0
        self.db.execute(
            'CREATE TABLE symbols (n INTEGER, codepoint TEXT)'
        )
        self.insert("0000")

    def insert(self, cp):
        insert = '{:0>8}'.format(cp)
        self.db.execute(
            'INSERT INTO symbols VALUES (?, ?)',
            (self.n, insert)
        )
        self.n += 1

    def commit(self):
        self.db_connection.commit()

    def close(self):
        self.db_connection.close()

    def get(self, x):
        self.db.execute('SELECT codepoint FROM symbols WHERE n = ?', (x,))
        return self.db.fetchone()[0]

def generate(ucd_file, db):
    '''Generate database file "db" from xml file "ucd_file" with "char" tags
    '''

    # Set up database
    db.create()

    # Parse XML file
    root = ET.parse(ucd_file).getroot()

    # Get Characters from UCD
    for i in root.findall('.//{%s}char' % UCD_XMLNS):
        # Get Character's code point and name
        cp = i.get('cp')
        na = i.get('na')
        
        # Test for no name or CJK character
        if na is None and i.get('kTotalStrokes') is None:
            continue

        # Test for Invalid Code Point and get value
        try:
            v = int(cp, 16)
        except TypeError: 
            continue

        # Stay at and below Plane 2
        if v >= 917504:
            continue

        # The character is what we're looking for, Insert it into the database
        db.insert(cp)

    # Finalize the database
    db.commit()

class Converter:
    '''Wrapper class for the database and convert functions'''

    def __init__(self, db):
        self.base = db.n - 1
        self.db = db

    def to_base_unicode(self, number):
        '''Convert base 10 number to list of descending place values'''
        a = []
        d = number
        while d != 0:
            r = d % self.base
            a = [r] + a
            d = d // self.base

        return a

    def to_codepoints(self, l):
        '''Get codepoints from database from values in base unicode'''
        return [self.db.get(i) for i in l]

    def get_utf8(self, cp):
        '''Individual character conversion'''
        return bytes('\\U' + cp, 'utf-8').decode('unicode_escape')

    def to_utf8(self, l):
        '''Convert list of codepoints to utf-8'''
        return ''.join([self.get_utf8(x) for x in l])
        

def main(force, ucd_file, db_file, numbers):
    # Initialize database
    db = Db(db_file)
    if force:
        db_file.unlink()
    
    if not db_file.is_file():
        print('Generating database... ', end='')
        sys.stdout.flush()
        db.connect()
        generate(ucd_file, db)
        print('{} symbols found'.format(db.n - 1))
    else:
        db.connect()
        db.count()

    # Initialize converter
    convert = Converter(db)
    if convert.base == -1:
        sys.exit(wrap(
            'Invalid database, you must use "-f" or "--force" to regenerate'
            'the database,'
            'using the xml file provided or another valid Unicode Character'
            'Database XML file.'
        ))
    print('base:', convert.base)

    # Process number arguments
    for number in numbers:
        values = convert.to_base_unicode(number)
        codepoints = convert.to_codepoints(values)
        print('{}: "{}"'.format(number, convert.to_utf8(codepoints)))

    db.close()

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(description=(
        'Converts normal base 10 numbers into a base 121,003 number that uses'
        'the order and characters of Unicode and outputs it as utf-8.'
    ))

    parser.add_argument(
        '-x', '--xml',
        metavar = 'XML_FILE',
        nargs=1,
        type=Path,
        default = [Path(UCD_FILE)],
    )

    parser.add_argument(
        '-f', '--force',
        default = False,
        action = 'store_true',
        help='Remove the database if it exists and regenerate it.'
    )

    parser.add_argument(
        'numbers',
        metavar = 'NUMBER',
        type=int,
        nargs='*',
    )

    args = parser.parse_args()

    main(args.force, args.xml[0], Path(DB_FILE), args.numbers)

