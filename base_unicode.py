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
    def __init__(self):
        pass

    def count(self):
        self.db.execute('SELECT COUNT(*) FROM symbols')
        self.n = self.db.fetchall()[0][0]

    def connect(self):
        self.db_connection = sqlite3.connect(DB_FILE)
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

def generate(db):
    db.create()
    root = ET.parse(UCD_FILE).getroot()

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
    def __init__(self):
        db = Db()

        if not isfile(DB_FILE):
            print("Generating database... ", end="")
            sys.stdout.flush()
            db.connect()
            generate(db)
            print("{} symbols found".format(db.n - 1))
        else:
            db.connect()
            db.count()

        self.base = db.n - 1

        self.db = db

    def __call__(self, number):
        a = []
        d = number
        while d != 0:
            r = d % self.base
            a = [r] + a
            d = d // self.base

        return a

    def get_codepoints(self, l):
        return [self.db.get(x) for x in l]

    def get_utf8(self, cp):
        return bytes('\\U' + cp, "utf-8").decode("unicode_escape")

if __name__ == "__main__":
    convert = Converter()
    print("base:", convert.base)

    from sys import argv
    values = convert(int(argv[1]))
    print('Values of digits:', values)
    codepoints = convert.get_codepoints(values)
    print('Digit codepoints:', codepoints)
    print('"' + ''.join([convert.get_utf8(x) for x in codepoints]) + '"')
