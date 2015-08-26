'''
TorPages
---
This server software is used to allow individuals to publish static HTML/Text content to the DeepWeb without
cost, and without registration.

This software is licensed under the Kopimi concept, meaning this software is essentially public domain,
but it would be nice to refer to CaveFox Telecom and Michael Canning as it is always nice to receive credit
for work.

For more information contact Michael Canning - mcanning(at)tutanota(dot)com

Check out our GitHub repository and consider contributing [https://github.com/mcanningjr/TorPages]
'''

from flask import render_template   # Used to render HTML pages
from flask import Flask   # Core web server
from flask import request   # Used to process POST requests
import random   # Used to generate random page IDs
import os   # Used to check for/delete files
import uuid   # Used to generate the modification keys

app = Flask(__name__)   # Defines Flask Application


@app.route('/', methods=['GET'])   # This section deals with serving the home page of the service
def index():
    return(render_template('index.html'))


@app.route('/', methods=['POST'])   # This section deals with publishing content via POST requests
def postPage():
    code = request.form['code']   # Gets the HTML/Text from the POST request
    oldid = str(request.form['ID'])   # Gets the ID of the post (used if updating an existing page)
    key = str(request.form['key'])   # Gets the modification key (used if updating an existing page)
    customlink = str(request.form['customlink']).lower()   # Gets the custom page name (Optional when first posting a site)
    if os.path.isfile('templates/userpages/' + customlink + '.html') and customlink is not '':   # Checks to see if the custom link is taken if one is requested
        return 'Link is Taken!'
    if oldid is '':   # Checks to see if a new page is being posted, or if an old page is being updated
        newid = random.randint(1, 99999999999999999999)   # Generates a new page ID
        while os.path.isfile('templates/userpages/' + str(id) + '.html'):   # Checks to see if the ID is take and creates a new one if it is
            newid = random.randint(1, 99999999999999999999)
        if customlink is not '':    # Checks if the user set a custom post ID
            if ' ' in customlink or '?' in customlink or '#' in customlink or '$' in customlink or '@' in customlink or '%' in customlink:   # Checks custom string for common invalid characters
                return 'Custom Link Must Only Contain Letters, Underscores, Dashes, and Numbers'
            newid = customlink   # Redefines the ID to the custom one if a user chose one
        key = str(uuid.uuid4())   # Generates a new UUID for use as a modification key
        file = open('templates/userpages/' + str(newid) + '.html', 'w')   # Opens a new HTML file
        file.write(code)   # Writes code to HTML file
        file.close()   # Closes HTML file
        file = open('keys/' + str(newid) + '.key', 'w')   # Opens a new file to store the modification key
        file.write(key)   # Writes the key to file
        file.close()   # Closes the key file
        return render_template('return.html', ID=newid, key=key)   # Returns a page with the user's new page info
    else:   # This section is for modification of an existing page
        if os.path.isfile('keys/' + str(oldid) + '.key'):   # Checks to see if the page exists by checking for Mod Key Existence
            file = open('keys/' + str(oldid) + '.key', 'r')   # Opens the key file for verification
            realkey = file.read()   # Reads the key file and sets it as variable realkey
            file.close()   # Closes the keyfile
            if str(realkey) == str(key):   # Checks for a valid modification key
                os.remove('keys/' + str(oldid) + '.key')   # Removes the old key file if the key is valid
                newkey = str(uuid.uuid4())   # Generates a new modification key for increase security
                file = open('keys/' + str(oldid) + '.key', 'w')   # Opens the key file
                file.write(newkey)   # Writes the new key to the key file
                file.close()   # Closes the key file
                os.remove('templates/userpages/' + str(oldid) + '.html')   # Removes the old page
                file = open('templates/userpages/' + str(oldid) + '.html', 'w')   # Opens a new file for the page
                file.write(code)   # Writes the new code to the new key file
                file.close()   # Closes the key file
                return render_template('return.html', ID=oldid, key=newkey)   # Returns a page with the user's new page info
            else:   # Returns an error to the user is the modification key used is invalid
                return 'Invalid Key!'
        else:   # Returns an error if the page being modified never existed in the first place
            return 'Page Does Not Exist!'


@app.route('/p/<ID>', methods=['GET'])    # This section deals with GET requests for user pages
def getPage(ID):
    if os.path.isfile('templates/userpages/' + str(ID).lower()):   # Checks to see if the requested page exists
        return(render_template('userpages/' + str(ID).lower() + '.html'))   # The ID section of the request is converted to lower case
    else:   # Returns a 404 if the page does not exist
        return'Error 404: The requested page does not exist!'



@app.route('/rules', methods=['GET'])  # This section returns the rules page when requested
def getRules():
    return(render_template("rules.html"))


@app.route('/about', methods=['GET'])   # This section returns the about page when requested
def getAbout():
    return(render_template("about.html"))

app.run(debug=False)   # Starts the Flask server with debugging set to False
