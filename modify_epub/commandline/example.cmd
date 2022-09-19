:: This is an example of how to run the command line version of Modify ePub from a batch file
:: It assumes a single argument of the epub file to be modified, and will run just the
:: smarten punctuation feature against it, with reduced log output
::
:: e.g. example.cmd "myfile.epub"
calibre-debug -e me.py "%1" --smarten_punctuation
