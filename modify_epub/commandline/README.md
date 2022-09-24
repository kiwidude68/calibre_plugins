##  Running Modify ePub from the command line

### INTRODUCTION

The `me.py` script file is a Python script designed for calibre users
to allow running the Modify ePub plugin from the command line rather
than using the calibre gui.

It still requires calibre to be installed along with the Modify Plugin.

The intent is to allow this plugin to be used in a scenario where the user
does not want to add the books to calibre to use a feature of the plugin.
For instance you may just want to use the `smarten_punctuation` feature.

### INSTALLATION INSTRUCTIONS

1. Extract the `me.py` from this zip file into a folder of your choice
2. To see the options available to run the script, run the following:
```
calibre-debug -e me.py --help
```

### OTHER NOTES

- If you have a particular set of options you want to repeatedly run, you
  may want to wrap this script with your own batch file that just takes
  in the variable argument such as the path to the file. A very simple
  example can be found in `example.cmd` in the Modify ePub zip file.
- Two features of the GUI version of the plugin are not supported as they
  require calibre metadata which is unavailable from the command line:
    - add_replace_jacket
    - update_metadata

