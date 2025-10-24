import sys
from zipfile import ZipFile
p = sys.argv[1]
with ZipFile(p,'r') as z:
    for info in z.infolist():
        print(info.filename)
