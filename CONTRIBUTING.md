# Contributing to this Repository

> ALERT:
>
> All contributions to this repository **MUST** be made through [GitHub][contribute-url], which
> acts as the source of truth for all plugins. Please fork the repository from [here][contribute-url].

## Organization

Please reference the [README.md][readme-uri] for the file layout of this repository.

## Commit Checklist

Before you commit to GitHub and publish your plugin zip to MobileRead, make sure you:
- Update the version number in `__init__.py` (see below for numbering strategy).
- Update the `CHANGELOG.md`
- Comment out/remove any extra debug logging or temporary writing files to disk
- If you changed translatable text, run: `generate-pot.cmd`
- If you have a Transifex account, download latest translations with: `transifex-pull.cmd`
- Run `build.cmd` one last time to make sure every change is included in the zip file!

If this is an official release on the MobileRead plugin thread, then:
- Edit the first post in the forum thread:
    - Upload the zip attachment, replacing the previous (zip name should be identical)
    - Update the `[SPOILER]` containing the change history
    - If necessary amend/update the list of features or screenshots.
- Create a new post in the thread to alert forum users:
    - List the version and changes made.

---
## Plugin Version Numbering Guidelines

While there are no strict rules on which parts of the version number for a plugin to "bump" the following may prove a useful guide. The only thing that must happen is that the overall number increments with each new plugin release in order for the calibre Plugin Updater to show this for users to install.
> ``<Major>.<Minor>.<Build>`` e.g. 1.4.2
- **Major** is very rarely incremented, as it is reserved for massive plugin changes.
- **Minor** is the most common to increment, representing a new release to the community.
- **Build** will also be frequently changed, to represent an iteration within the release.

### Example:
- A current plugin release starts at ``v1.0.0``
- A new feature is added or significant change is made so we bump the Minor, releasing as ``v1.1.0``
- Feedback to a test version or bug fixes means a bump to the Build, releasing as ``v1.1.1``
- Later another new feature/change is made, releasing as ``v1.2.0`` and so on.

---
## PyQt / Python Compatibility

In setting up this repo I have decided to:
- **Drop PyQt4 support** 
    - All these plugins now require a minimum of at least **calibre v2.0** (from 2014)
    - Supporting PyQt4 involves too many edge cases and changes to Qt API syntax.
    - Users with 8+ year old calibre versions are a small % of the userbase!
- **Keep all PyQt5+ support**
    - The `qt.core` import syntax is absolutely the future way forward for these plugins.
    - It will reduce the maintainance required when Qt7 or later is introduced.
    - However it was only available from **calibre v5.13** (March 2021) or later.
    - Kovid has allowed the Qt6 calibre to work with PyQt5 imports as a courtesy only.
    - As at Sept 2022, only [66%](https://calibre-ebook.com/dynamic/calibre-usage) of calibre users have 5.22 or later.
    - So we will attempt to support all PyQt5 calibre versions (v2.0+) by using the following:
```
try:
    from qt.core import xxx
except ImportError:
    from PyQt5.Qt import xxx
```

Some basic testing has been done against the minimum versions for all these plugins to confirm the plugin loads. It is possible there are other more subtle issues that come out. Worst case we will just move a plugin forward to require a later minimum version if the backwards support is too hard.

---

## Getting Started

Some of the plugin maintainers may not be quite so familiar with working with Git or GitHub. Note that there are many ways you can approach this. Here are a few suggestions for those of you working on Windows:

- Install the Git tools, the obvious choice being [Git for Windows](https://gitforwindows.org/)
- [Visual Studio Code](https://code.visualstudio.com/) can give you even easier tools for reviewing and committing changes.
- VS Code can [integrate directly with GitHub](https://code.visualstudio.com/docs/editor/github)
- Alternatively just clone this repo to a folder on your machine.
- If you are a point-and-click in Windows Explorer sort of person then I recommend [TortoiseGit](https://tortoisegit.org/).

### Plugin Batch Files

Each plugin folder contains the following batch files in a ``.build`` subfolder to make development less painful. The batch files should be run from within that folder.

| Batch file | Purpose |
| ---------- | ------- |
| `build.cmd` | Compile the translations into .mo files, copy common files, construct the plugin zip, install in calibre.
| `debug.cmd` | Same as `build.cmd` with the addition of launching calibre in debug mode. Also useful for testing translations.
| `generate-pot.cmd` | Generate the latest `.pot` file for translators to work with. See the Plugin Translations section below.
| `transifex-pull.cmd` | Download the latest available translations for this plugin from Transifex.

Mostly you will be using `debug.cmd`. This allows you to see any errors when calibre attempts to load the plugin zip (e.g. in the VS Code console window), and then interactively test the plugin. Close calibre manually when you are finished testing.

All these batch files can be run from within VS Code using tasks - see below.

### Submitting Changes

The management of this repo will be kept as simple as possible:
- There will be just one branch (main).
- No pull requests/reviews workflow.
- Trusted contributors will be able to commit changes for official releases.
- Casual maintainers can choose to submit patch files or zips to the official maintainers with their changes.

The zip files for these plugins are published via the [MobileRead calibre plugin forum](https://www.mobileread.com/forums/forumdisplay.php?f=237) threads.
- The official plugin zip that all users can download via calibre itself is attached to the first post in each plugins thread.
- Only the plugin thread owner or a MobileRead admin can modify that post.
- Plugin authors or contributors may choose to submit other versions (betas etc.) within the thread. 

---
## Plugin Translations

Almost all of kiwidude's plugins will now support translations via the [Transifex](https://www.transifex.com/) website, just like calibre itself does. A huge thanks and shout out to all the translators out there who donate their time to assist with this.

### Translations in short

- If you add or modify any translatable strings in a plugin then we need to regenerate the `.pot` file for it by running the `generate-pot.cmd` batch file.
- The Transifex website will automatically import that updated `.pot` file once you commit it to GitHub.
- If translators have new/updated translations available, we need to periodically download/recompile the translations to include them in a new plugin version.

### Translation workflow in detail

- The translatable strings in the source code are marked with `_()` in `.py` files that include a call to `load_translations()` at the top.
- We generate a `.pot` file for the plugin which lists all those translatable strings using the `generate-pot.cmd` batch file.
- The developer can commit their changes to git at this point so the updated `.pot` file is in GitHub.
- The [Transifex](https://www.transifex.com/) website will be configured to detect the updated `.pot` file in GitHub and import it for each plugin.
- Translators for the calibre-plugins project are notified and can now upload their translations.
- To update the plugin, the developer runs the `transifex-pull.cmd` batch file to download the `.po` files from Transifex (requires an account - see below).
- The developer rebuilds the plugin zip file with the latest compiled `<lang>.mo` files using `build.cmd`.
- Alternatively the developer can test with a specific language by modifying and running `debug.cmd` (see below).

### Getting Started with Transifex

If you want to publish the latest translations for a plugin you will need to:
- Create an account (free!) at https://www.transifex.com/
- Join the [calibre-plugins](https://www.transifex.com/calibre/calibre-plugins/) project.
- Download the [Transifex CLI client](https://github.com/transifex/cli/releases). 
- Unzip the CLI client and place the `tx.exe` somewhere in your path.
- Generate an [API token](https://www.transifex.com/user/settings/api/) to your clipboard. 
- Run the `transifex-pull.cmd` for a plugin, which will prompt you the very first time for your API token above.

### Testing Translations

- You can modify the `debug.cmd` file to the language you want to test. Please revert such changes afterwards!
```
SET CALIBRE_OVERRIDE_LANG=pl
```

Testing tips from JimmXinu:
- In FFF I added a fake zz.po (https://github.com/JimmXinu/FanFicFare/tree/main/calibre-plugin/translations) language, and used a perl script to just append zz to every translatable string.  Then when you run with CALIBRE_OVERRIDE_LANG=zz you can use that to see whether you got them all working or not.
- If you are old school and use %s replacements in translated strings, watch for those when translations come in. I've seen some hard to find problems with translated strings had too few or too many %d or %s in them.

### Translation Tips

- The Transifex configuration is stored in the `.tx\config` file for each plugin
- Be aware that Transifex may change {{config}} file syntax with newer CLI versions. I know v1.3.0 works currently with this repo.
- If you add translatable text for the first time to an existing .py file (or new file) you must modify `generate-pot.cmd` to include that filename in the list of files it scans.
- Setting these plugins up in Transifex for the first time required me to be an administrator. You would need to contact Kovid Goyal as the calibre organisation owner for any new plugins for similar rights.

### Useful Translation Documentation

- [calibre translation FAQ](https://calibre-ebook.com/get-involved)
- [calibre plugin translation docs](https://manual.calibre-ebook.com/creating_plugins.html#adding-translations-to-your-plugin)
- [mobileread thread on calibre in Transifex](https://www.mobileread.com/forums/showthread.php?t=239995)
- [Transifex CLI docs](https://developers.transifex.com/docs/cli)
- [Transifex GitHub monitoring docs](https://docs.transifex.com/projects/updating-content)


---
## Working with Visual Studio Code

Originally these plugins were developed using the Eclipse IDE. However nowadays I much prefer using VS Code, so instructions here will be focused around using that. You can use any text editor you like to modify these plugins - it really doesn't matter and depends on how much intellisense support you are after and what you feel most productive with. If you did use something else though please make sure that any local workspace files that editor creates are excluded in the `.gitignore` to keep the noise away from others.

Setting up Python itself is not covered here, that is a straightforward and well documented elsewhere.

If however you are wanting to attach a debugger to a running calibre process for full stepping through code etc that is not what VS Code does. Your debugging is going to be limited to `print()` and `log` statements. If you think you need more interactive debugging then this thread may offer some tips:
[A free Calibre Windows development environment using Visual Studio](https://www.mobileread.com/forums/showthread.php?t=251201)

### Navigating calibre in VS Code

Entirely optional but you might find it useful to have the calibre source code easily accessible in addition to this plugins repo. Particularly when you need to understand the calibre API or look to see how it should be used.

To start you should clone the [calibre source code](https://github.com/kovidgoyal/calibre.git) repository to your machine to a `calibre` folder.

### Option A: To search calibre source code and this code repo together in VS Code explorer
- After cloning, move this repo `calibre_plugins` folder to sit within the `calibre\src` repo subfolder above. 
- Your local folder should look like this:
```
calibre
  ...
  src
    calibre
    calibre_plugins
    ...
```
- Open the `calbre\src` folder as your workspace folder in VS Code. That will include both the `calibre` and `calibre_plugin` subfolders
- This approach can be handy if you want are doing a lot of searching of calibre code for how to use a function etc.

### Option B: To focus on just these plugins, with ctrl+click navigation to calibre source

- Create a `.env` file in the root of your workspace (e.g. in this repo folder root where this README is located)
- Set the contents to be the following, with the full path to your `calibre\src` folder:
```
PYTHONPATH=<path_to_calibre_src>
```
- Create/modify your `.vscode\settings.json` to point to this file with at least this: 
```
{
    "python.envFile": "${workspaceFolder}/.env"
}
```
- Now when browsing plugin code, all linting warnings for calibre python functions should be resolved. 
- You can ctrl+click to navigate into calibre source code, yay!.
- This option is useful if you are focused on some quick plugin changes and want a more lightweight VS Code workspace.

You can of course do both of the above or mixing and matching - for instance the same approach for using a `.env` file could be used if you wanted to open just one plugin subfolder within this repo in VS Code. See [Using Python environments in VS Code](https://code.visualstudio.com/docs/python/environments)

### Virtual Environments

The above approach will allow resolving calibre imports but not third party libraries such as PyQt5 or lxml. If you want intellisense for those, then you need a few more steps to create a virtual Python environment in VS Code.

1. From the powershell prompt in VS Code with the workspace loaded, run:
```
py -3 -m venv .venv
.venv\scripts\activate
```
2. Now you can try to install third party packages you see a plugin requires, e.g.
```
python -m pip install PyQt5
python -m pip install lxml
...
```
For more information, see: [Getting Started with Python in VS Code](https://code.visualstudio.com/docs/python/python-tutorial)

### Running .cmd files as VS Code Tasks

For those of you who are not command line warriors, the repository includes a ``.vscode/tasks.json`` file for use by the VS Code IDE to run any of the plugin batch files in an easy fashion.

The keyboard shortcut default is **Alt + Shift + F10** to bring up the list to choose from, then hit Enter.

Documentation: [Integrate with External Tools via Tasks](https://code.visualstudio.com/docs/editor/tasks)

[readme-uri]: README.md
[contribute-url]: https://github.com/kiwidude68/calibre_plugins