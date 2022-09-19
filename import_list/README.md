# Import List Plugin
[![MobileRead][mobileread-image]][mobileread-url]
[![History][changelog-image]][changelog-url] 
[![License][license-image]][license-url]
[![calibre Version][calibre-image]][calibre-url]
[![Status][status-image]][status-image] 

## Overview

This wizard-based plugin allows you to match existing or create empty books in calibre based on lists of books from external sources. For some users it may be they want to import an existing list of their own reading/books, for others it can be that they want to import lists of bestsellers, popular books, genre recommendations, award winners and so on. Once matched you can integrate with the [Reading List](https://www.mobileread.com/forums/showthread.php?t=134856) plugin to record as a list to read, send to a device or just view on screen.

- **Import from Clipboard** - paste in a list of book title/authors copied to your clipboard, such as from a website forum post of favourite books.
- **Import from CSV File** - many users have lists of books stored in applications like Excel which can export to CSV, or use websites like Goodreads/Library Thing which also have export to CSV capability.
- **Import from Web Page** - over 100 predefined websites are configured (including Goodreads, Amazon etc) or you can add your own. Included in the predefined websites is Fantastic Fiction, which can be an easy way to scrape title, author, series and pubdate metadata for all books by an author. Note that for this and any of the predefined websites that you are not limited to the specific URL configured. You can navigate to the website page of interest in your browser, then drag/drop or copy the URL into the Website tab of this plugin. most websites use the same layout for their webpages so no other configuration needs to be changed.

Using the wizard is a three step process (more detail in examples below):

- **STEP 1:** Select/configure a list source - either choose a predefined source or configure your own.
- **STEP 2:** Resolve matches - the plugin uses fuzzy logic algorithms to best match against existing books in your library. You can then fine tune the results with further searches and/or choose to add empty books for those that do not exist in your library.
- **STEP 3:** Display/save the results - with the matched results you can create/append to a Reading List plugin list or just display temporarily on screen. You also have the option of saving your customized configuration as user settings for future reuse.

## Main Features

- Import lists of books from Clipboard, CSV files or websites.
- Choose from over 100 predefined websites and/or add your own configurations.
- Import into standardfields, identifiers or custom columns
- Option to update metadata of existing books
- Predefined websites can be viewed as a list or grouped by category
- Websites can be directly opened in a web browser
- Supports importing title, author, series, series index and pubdate (all but title are optional)
- Customise clipboard imports with regular expressions (common examples available on a dropdown)
- Customise CSV imports to define the numbered column and other options such as delimiters.
- Customise website imports using XPath expressions, with highlighting available to show matches.
- Website URLs support template expressions to allow automatic substitution of values such as dates. For an example look at the Goodreads Popular This Month/Year settings.
- Automatically match books in your library using a progression of identical/similar/fuzzy matching algorithms
- User can manually search/refine matches, create empty books, remove books from the list etc.
- Optionally put the resulting matched books into a list for use with the Reading List plugin, or just display on screen
- Configurations can be exported/imported for sharing with other users.


## Usage Examples

### Example 1: Workflow for importing from a website

- Choose the Predefined setting tab
- To see the webpage in your browser for that site, click on the Browser button (optional step)
- Double-click or click "Preview" to see the titles/authors for that website link
- Click Next to see what books have automatically been matched against those in your library. It uses a variety of special fuzzy algorithms to attempt this initial pass.
- For any books that haven't yet matched, you can double-click on them in the top grid to execute a calibre search showing results in the bottom. Refine the search if needed and double-click on the book in the bottom to select it as the match. Alternatively you can add an empty book or remove that book from the list. Of course you don't have to match/delete every book - it is up to you how much of the "list" you want to keep before moving to the next wizard step.
- Click Next to be given the choice of optionally saving all the matched books to a reading list. You can also save your list configuration (more relevant when using your own list sources).
- Click Finish to see the books displayed in your library.

### Example 2: Getting books for an author from Fantastic Fiction

- Bring up the web page for that author in your browser. I suggest using the Search the Internet plugin as the fastest way of doing so.
- Start the Import List plugin
- From the Predefined tab, choose the "Fantastic Fiction" setting and click Edit
- Either drag/drop or paste the url from your browser into the "Download from url" combo at the top of the Web Page tab.
- Click Preview again to see what titles/authors have been extracted, then Next to continue with the rest of the wizard as per the instructions above.

### Example 3: Loading books from the clipboard

- Use the Clipboard tab.
- Paste in your text
- Specify your regular expression to extract the title/author. At a minimum you must have a title.
- Some predefined expressions are available to help in the script button to the right of the dropdown.
- Click Preview again to see what titles/authors have been extracted, then Next to continue with the rest of the wizard as per the instructions above.

### Example 4: Load from a CSV file

- Use the CSV File tab.
- Browse to the file, click Preview and the columns should be displayed.
- Alter your separator if required and specify the title/author column numbers.
- Click Preview again to see what titles/authors have been extracted, then Next to continue with the rest of the wizard as per the instructions above.

### Example 5: Scrape from a custom website

- Select the Web Page tab.
- Click the Clear button to remove any previous website settings.
- Drag/drop or paste the url into the Url combobox.
- Click preview to see the underlying html that you will be specifying XPath expressions for.
- You might find it useful to get to the part of the source html of interest by using the "Find" text in this dialog, typing for instance the first book name in the list and clicking on the Find button.
- You can *either* specify an XPath to what I call a "row" for each book, and then use a relative XPath to the title/author, *or* you can just specify a direct XPath to the title/author. It depends on the site as to which approach works best.
- Use the marker icon on the right of each XPath combo to preview what text your expression is going to select. You can step forward/backward through the matches.
- Your Title and Author expressions must extract the text(). The optional regular expression in the Strip field will then be applied, along with a number of special cleanups coded within the plugin to strip common unnecessary characters.
- If desired you can reverse the list order - for instance a countdown from 50 to 1 on the web page you might want in your list as 1 to 50.
- There are some additional complex options for dealing some difficult websites which use non utf-8 encodings, or require javascript to execute to load the page content. Some Amazon pages make use of these settings for an example.
- Click Preview again to see what titles/authors have been extracted, then Next to continue with the rest of the wizard as per the instructions above.

## Development / Contributions

All kiwidude's calibre plugins are now developed and maintained in GitHub at:
- https://github.com/kiwidude68/calibre_plugins

Please see the README.md and CONTRIBUTING.md at the above site for more information.


[mobileread-image]: https://img.shields.io/badge/MobileRead-Plugin%20Thread-blue?logo=data:image/x-icon;base64,AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAQAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAns32/zqT5v8SeeD/Enng/xJ54P8SeeD/LYvl/3+78v8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZazv/xJ54P8SeeD/Enng/zqT5v9Jm+n/HoLi/xJ54P8SeeD/OpPm/wAAAAAAAAAAAAAAAAAAAAAAAAAAzub7/xJ54P8SeeD/Enng/4/D9P/p6en/0tLS/8Tc8P8SeeD/Enng/xJ54P+Pw/T/AAAAAAAAAAAAAAAAAAAAAL3e+v8SeeD/Enng/xJ54P+93vr/Wlpa/zc3N/8AAAAAEnng/xJ54P8SeeD/f7vy/wAAAAAAAAAAAAAAAAAAAAAAAAAAHoLi/xJ54P8SeeD/T3+r/yQkJP9+jpz/Zazv/xJ54P8SeeD/Enng/73e+v8AAAAAAAAAAAAAAAAAAAAAz8Kt/66uof+Gj4L/ho+C/5SKb/+Vh2j/ho+C/4aPgv+Gj4L/ho+C/5OVgv+6qYP/yryi/wAAAAAAAAAAp5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv8AAAAA6ePb46eQVv+nkFb/p5BW/6eQVv+nkFb/xLWY/8/Crf/Pwq3/vq6N/7qogv+6qIL/uqiC/7qogv+nkFb/5uDW/+bg1v+nkFb/p5BW/6eQVv+nkFb/p5BW/+zn4f///////////8zMzP92dnb/VFRU/9nZ2f//////taJ5/8/Crf/m4Nb/p5BW/6eQVv+nkFb/p5BW/6eQVv/m4Nb////////////MzMz/k5OT/8zMzP/z8/P//////8S1mP/EtZj/5uDW/6eQVv+nkFb/p5BW/6eQVv+nkFb/oZ6Z/5OTk//m5ub/////////////////8/Pz/3Z2dv9xcHD/j4h7/9rRwf+nkFb/p5BW/6eQVv+nkFb/VVNP/8zMzP/z8/P/dnZ2/9nZ2f///////////5OTk//z8/P//////3Rxa//Pwq3/p5BW/6eQVv+nkFb/p5BW/2FgYP///////////76+vv/MzMz///////////+ioqL/oqKi/76+vv91b2X/z8Kt/6eQVv+nkFb/p5BW/6eQVv+JfWX/bGtq/4WFhf+FhYX//////////////////////76+vv++vr7/taJ5/8/Crf+nkFb/p5BW/6eQVv+nkFb/p5BW/8m7ov//////+Pb1/+bg1v/g2Mz/z8Kt/8/Crf+6qIL/uqiC/6eQVv/m4Nb/uqmD/7qpg/+nkFb/p5BW/6eQVv+nkFb/rZZh/7qpg/+/r43/z8Kt/8/Crf/m4NYd5uDWVQAAAAAAAAAA8A8AAOAHAADAAwAAwEMAAOADAADAAQAAgAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAA==
[mobileread-url]: https://www.mobileread.com/forums/showthread.php?t=187831

[changelog-image]: https://img.shields.io/badge/History-CHANGELOG-blue.svg
[changelog-url]: CHANGELOG.md

[license-image]: https://img.shields.io/badge/License-GPL-yellow.svg
[license-url]: ../LICENSE.md

[calibre-image]: https://img.shields.io/badge/calibre-2.0.0-green
[calibre-url]: https://www.calibre-ebook.com/

[status-image]: https://img.shields.io/badge/Status-Stable-green