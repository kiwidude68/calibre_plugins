#!/usr/bin/python

__license__   = 'GPL v3'
__copyright__ = '2022, Grant Drake'

'''
Creates a GitHub release for a plugin, including uploading the zip file.

Invocation should be via each plugin release.cmd, which will ensure that:
- Working directory is set to the <plugin> subfolder
- Zip file for plugin is rebuilt for latest local code/translations
- Pass through the CALIBRE_GITHUB_TOKEN environment variable value
'''

import sys, os, re, json
from urllib import request, parse, error

API_REPO_URL = 'https://api.github.com/repos/kiwidude68/calibre_plugins'

def readPluginDetails():
    shortName = os.path.split(os.getcwd())[1]
    initFile = os.path.join(os.getcwd(), '__init__.py')
    if not os.path.exists(initFile):
        print('ERROR: No __init__.py file found for this plugin')
        raise FileNotFoundError(initFile)
    
    pluginName = None
    with open(initFile, 'r') as file:
        content = file.read()
        nameMatches = re.findall(r"\s+name\s*=\s*\'([^\']*)\'", content)
        if nameMatches: 
            pluginName = nameMatches[0]
        else:
            raise RuntimeError('Could not find plugin name in __init__.py')
        versionMatches = re.findall(r"\s+version\s*=\s*\(([^\)]*)\)", content)
        if versionMatches: 
            version = versionMatches[0].replace(',','.').replace(' ','')

    print('Plugin v%s to be released for: \'%s\''%(version, pluginName))
    return shortName, pluginName, version

def getPluginZipPath(pluginName):
    zipFile = os.path.join(os.getcwd(), pluginName+'.zip')
    if not os.path.exists(zipFile):
        print('ERROR: No zip file found for this plugin at: {}'.format(zipFile))
        raise FileNotFoundError(zipFile)
    return zipFile

def readChangeLogForVersion(version):
    changeLogFile = os.path.join(os.getcwd(), 'CHANGELOG.md')
    if not os.path.exists(changeLogFile):
        print('ERROR: No change log found for this plugin at: {}'.format(changeLogFile))
        raise FileNotFoundError(changeLogFile)
    
    with open(changeLogFile, 'r') as file:
        content = file.readlines()
    
    foundVersion = False
    changeLines = []
    for line in content:
        if not foundVersion:
            if line.startswith('## ['+version +']'):
                foundVersion = True
            continue
        # We are within the current version - include content unless we hit the previous version
        if line.startswith('## ['):
            break
        changeLines.append(line)

    if len(changeLines) == 0:
        print('ERROR: No change log details found for this version: {}'.format(version))
        raise RuntimeError('Missing details in changelog')

    # Trim trailing blank lines
    while changeLines and len(changeLines[-1]) <= 2:
        changeLines.pop()

    print('ChangeLog details found: {0} lines'.format(len(changeLines)))
    return ''.join(changeLines)

def checkIfReleaseExists(apiToken, tagName):
    # If we have already released this plugin version then we have a problem
    # Most likely have forgotten to bump the version number?
    endpoint = API_REPO_URL + '/releases/tags/' + tagName
    req = request.Request(url=endpoint, method='GET')
    req.add_header('accept', 'application/vnd.github+json')
    req.add_header('Authorization', 'BEARER {}'.format(apiToken))
    try:
        print('Checking if GitHub tag exists: {}'.format(endpoint))
        with request.urlopen(req) as response:
            response = response.read().decode('utf-8')
            raise RuntimeError('Release for this version already exists. Do you need to bump version?')
    except error.HTTPError as e:
        if e.code == 404:
            print('Existing release for this version not found, OK to proceed')
        else:
            raise RuntimeError('Failed to check release existing API due to:',e)

def createGitHubRelease(apiToken, pluginName, tagName, changeBody):
    endpoint = API_REPO_URL + '/releases'
    data = {
        'tag_name': tagName,
        'target_commitish': 'main',
        'name': '{} v{}'.format(pluginName, version),
        'body': changeBody,
        'draft': False,
        'prerelease': False,
        'generate_release_notes': False
    }
    data = json.dumps(data)
    data = data.encode()
    req = request.Request(url=endpoint, data=data, method='POST')
    req.add_header('accept', 'application/vnd.github+json')
    req.add_header('Authorization', 'BEARER {}'.format(apiToken))
    req.add_header('Content-Type', 'application/json')
    try:
        print('Creating release: {}'.format(endpoint))
        with request.urlopen(req) as response:
            response = response.read().decode('utf-8')
            content = json.loads(response)
            htmlUrl = content['html_url']
            uploadUrl = content['upload_url']
            return (htmlUrl, uploadUrl)
    except error.HTTPError as e:
        raise RuntimeError('Failed to create release due to:',e)

def uploadZipToRelease(apiToken, uploadUrl, zipFile, tagName):
    downloadZipName = tagName+'.zip'
    endpoint = uploadUrl.replace('{?name,label}','?name={}&label={}'.format(downloadZipName, downloadZipName))
    with open(zipFile, 'rb') as file:
        content = file.read()

    req = request.Request(url=endpoint, data=content, method='POST')
    req.add_header('accept', 'application/vnd.github+json')
    req.add_header('Authorization', 'BEARER {}'.format(apiToken))
    req.add_header('Content-Type', 'application/octet-stream')
    try:
        print('Uploading zip for release: {}'.format(endpoint))
        with request.urlopen(req) as response:
            response = response.read().decode('utf-8')
            content = json.loads(response)
            downloadUrl = content['browser_download_url']
            print('Zip uploaded successfully: {}'.format(downloadUrl))
    except error.HTTPError as e:
        raise RuntimeError('Failed to upload zip due to:',e)


if __name__=="__main__":
    
    apiToken = sys.argv[1]
    if not apiToken:
        raise RuntimeError('No GitHub API token found. Please set it in CALIBRE_GITHUB_TOKEN variable.')

    (shortName, pluginName, version) = readPluginDetails()
    tagName = shortName + '-v' + version
    checkIfReleaseExists(apiToken, tagName)

    zipFile = getPluginZipPath(pluginName)
    changeBody = readChangeLogForVersion(version)

    (htmlUrl, uploadUrl) = createGitHubRelease(apiToken, pluginName, tagName, changeBody)
    uploadZipToRelease(apiToken, uploadUrl, zipFile, tagName)
    print('Github release completed: {}'.format(htmlUrl))