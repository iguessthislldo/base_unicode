import sys

# XML
import xml.etree.ElementTree as ET

# Database
import sqlite3
from os.path import isfile
from os import remove

# Xml file
UCD_FILE = 'ucd.all.grouped.xml'
UCD_XMLNS = 'http://www.unicode.org/ns/2003/ucd/1.0'

# Output database
DB_FILE = 'db'

class Db:
    def __init__(self, file):
        self.file = file

    def count(self):
        self.db.execute('SELECT COUNT(*) FROM symbols')
        self.n = self.db.fetchall()[0][0]

    def connect(self):
        self.db_connection = sqlite3.connect(self.file)
        self.db = self.db_connection.cursor()
    
    def create(self):
        self.n = 0
        self.db.execute((
            "CREATE TABLE symbols (n INTEGER, codepoint TEXT)"
        ))
        self.insert("0000")

    def insert(self, cp):
        insert = '{:0>8}'.format(cp)
        self.db.execute('INSERT INTO symbols VALUES (?, ?)', (self.n, insert))
        self.n += 1

    def commit(self):
        self.db_connection.commit()

    def close(self):
        self.db_connection.close()

    def get(self, x):
        self.db.execute('SELECT codepoint FROM symbols WHERE n = ?', (x,))
        return self.db.fetchone()[0]

def generate(ucd_file, db):
    db.create()
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

        #print("%s    %s    \"%s\"" % (cp, na, chr(v)))
        db.insert(cp)

    db.commit()

class Converter:
    def __init__(self, db):
        self.base = db.n - 1
        self.db = db

    def to_base_unicode(self, number):
        a = []
        d = number
        while d != 0:
            r = d % self.base
            a = [r] + a
            d = d // self.base

        return a

    def to_codepoints(self, l):
        return [self.db.get(i) for i in l]

    def get_utf8(self, cp):
        return bytes('\\U' + cp, "utf-8").decode("unicode_escape")

    def to_utf8(self, l):
        return ''.join([self.get_utf8(x) for x in l])
        

def main(force, ucd_file, db_file, numbers):
    # Initalize database
    db = Db(db_file)
    if force:
        remove(db_file)
    
    if not isfile(db_file):
        print("Generating database... ", end="")
        sys.stdout.flush()
        db.connect()
        generate(ucd_file, db)
        print("{} symbols found".format(db.n - 1))
    else:
        db.connect()
        db.count()

    # Initalize converter
    convert = Converter(db)
    print("base:", convert.base)

    # Process arguments
    for number in args.numbers:
        values = convert.to_base_unicode(number)
        codepoints = convert.to_codepoints(values)
        print('{}: "{}"'.format(number, convert.to_utf8(codepoints)))

    db.close()

if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()

    parser.add_argument(
        '-x', '--xml',
        metavar = 'XML_FILE',
        nargs=1,
        default = [UCD_FILE],
    )

    parser.add_argument(
        '-f', '--force',
        default = False,
        action = 'store_true',
    )

    parser.add_argument(
        'numbers',
        metavar = 'NUMBER',
        type=int,
        nargs='*',
    )

    args = parser.parse_args()

    main(args.force, args.xml[0], DB_FILE, args.numbers)

