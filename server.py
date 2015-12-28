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
from flask import session   # Used to handle logins
from flask import redirect   # Used to handle redirecting
import random   # Used to generate random page IDs
import os   # Used to check for/delete files
import hashlib   # Used to hash the website modification keys
import pickle
import bcrypt   # Used to encrypt the user passwords

app = Flask(__name__)   # Defines Flask Application


site_url = 'SITE_URL_GOES_HERE'
admin_email = 'ADMIN_EMAIL_GOES_HERE'
active = []   # Used to keep a list of logged in users
record = {}   # Used to keep a list of pages, and their owners for the admins
if os.path.isfile("pages.data"):   # checks to see if the file that stores the record dictionary exists
    record = pickle.load(open("pages.data", "rb"))   # Loads the record dictionary
else:
    pickle.dump(record, open("pages.data", "wb"))   # Creates the record dictionary


administrators = ['ADMIN_ACCOUNTS_GO_HERE']   # Define the administrator accounts


@app.route("/", methods = ["GET"])
def getindex():   # This section returns the index page or the management page if the user is logged in
    if session.get('username') in active:
        return(redirect("/manage"))
    return(render_template("index.html", admin_email=admin_email))


@app.route("/register", methods = ["POST"])
def registeradd():   # This section deals with registering new users
    username = request.form["username"]
    password = request.form["password"]
    password2 = request.form["confirm_password"]
    if username.isalnum() is False:
        return("That Username is Invalid!")
    if password != password2:
        return("The Passwords Entered Do Not Match!")
    else:
        if os.path.isfile("userdata/" + username + ".password"):   # Checks to see of the username's password file exists
            return("That Username Has Already Been Taken!")
        else:
            salt = bcrypt.gensalt(14)   # Generates the password salt
            hashedPassword = str(bcrypt.hashpw(str(password), salt))   # Hashes the password
            pickle.dump(salt, open("userdata/" + username + ".salt", "wb"))   # Saves the password salt
            pickle.dump(hashedPassword, open("userdata/" + username + ".password", "wb"))   # Sves the hashed password
            ownedSites = []
            pickle.dump(ownedSites, open("userdata/" + username + ".sites", "wb"))   # Saves a blank list of owned sites
            session['username'] = username   # Logs the user in
            return(redirect("/manage"))   # Redirects the user to the management page


@app.route("/register", methods = ["GET"])   # Returns the registration page
def registerget():
    return(render_template("register.html"))


@app.route("/legacy", methods = ["GET"])   # This section returns the legacy import page if the user is logged in
def legacyget():
    try:
        if session.get("username") in active:
            return(render_template("legacy.html", username = session.get('username')))
        else:
            return(redirect("/login"))
    except:
        return(redirect("/login"))


@app.route("/legacy", methods = ["POST"])
def legacypost():   # This section deals with importing pages under the old system nto the new system
    try:
        if session.get("username") in active:
            postID = request.form["postID"]
            postKey = request.form["postKey"]
            key = str(hashlib.sha512(str(postKey)).hexdigest())   # Gets the modification key (used if updating an existing page)
            if os.path.isfile('keys/' + str(postID) + '.key'):   # Checks to see if the page exists by checking for Mod Key Existence
                file = open('keys/' + str(postID) + '.key', 'r')   # Opens the key file for verification
                realkey = str(file.read())  # Reads the key file and sets it as variable realkey
                file.close()   # Closes the keyfile
                if str(realkey) == str(key) or str(postKey) == str(realkey):   # Checks for a valid modification key
                    sites = pickle.load(open("userdata/" + str(session.get("username")) + ".sites", "rb"))
                    sites.append(str(postID))   # Adds the site to the user's owned sites list
                    pickle.dump(sites, open("userdata/" + session.get('username') + ".sites", "wb"))   # Saves the user's sites list
                    record.update({str(postID): session.get("username")})   # Updates the record dictionary
                    pickle.dump(record, open("pages.data", "wb"))   # Saves the record dictionary
                    os.remove("keys/" + str(postID) + '.key')   # Removes the key file
                    return(redirect('/manage'))   # Returns a page with the user's new page info
                else:   # Returns an error to the user is the modification key used is invalid
                    return 'Invalid Key!'
            else:   # Returns an error if the page being modified never existed in the first place
                return 'Page Does Not Exist!'
        else:
            return(redirect("/login"))
    except:
        return(redirect("/login"))


@app.route("/login", methods = ["GET"])   # Returns the login page when requests
def loginget():
    return(redirect('/'))


@app.route("/login", methods = ["POST"])   # This section logs in the user
def loginpost():
    username = request.form["username"]
    password = request.form["password"]
    if os.path.isfile("userdata/" + username + ".password"):   # Checks to see if the user exists
        salt = pickle.load(open("userdata/" + username + ".salt", "rb"))
        passwordCheck = pickle.load(open("userdata/" + username + ".password", "rb"))   # Loads the stored password
        hashed = str(bcrypt.hashpw(str(password), salt))
        if str(hashed) != str(passwordCheck):   # Verifies the password
            return("The Password That Was Entered Was Incorrect!")
        else:
            session.pop('username', None)   # Removes any session that exists
            session['username'] = username   # Sets the session
            return(redirect('/manage'))   # Sends the user to the management page
    else:
        return("That User Does Not Exist!")


@app.route("/logout", methods = ["GET"])   # Logs out the user
def logout():
    active.remove(session.get('username'))   # Removes the user from the active users list
    session.pop('username', None)   # Closes the user's session
    return(redirect('/'))


@app.route("/create", methods = ["GET"])   # Returns the create a news page page
def createget():
    return(render_template("new.html", site_url = site_url, username = session.get('username')))


@app.route("/create", methods = ["POST"])
def createpost():
    if session.get('username') not in active:   # Checks to see if the user is logged in
        return('Please Login to Create a Page')
    customlink = str(request.form['customlink']).lower()   # Gets the custom page name (Optional when first posting a site)
    if os.path.isfile('templates/userpages/' + customlink + '.html') and customlink is not '':   # Checks to see if the custom link is taken if one is requested
        return 'Link is Taken!'
    newid = random.randint(1, 99999999999999999999)   # Generates a new page ID
    while os.path.isfile('templates/userpages/' + str(id) + '.html'):   # Checks to see if the ID is take and creates a new one if it is
        newid = random.randint(1, 99999999999999999999)
    if customlink is not '':    # Checks if the user set a custom post ID
        if customlink.isalnum() is False:   # Checks custom string for common invalid characters
            return 'Custom Links Must Only Contain Letters, and Numbers'
        newid = customlink   # Redefines the ID to the custom one if a user chose one
    file = open('templates/userpages/' + str(newid) + '.html', 'w')   # Opens a new HTML file
    file.write(request.form["code"].encode('utf-8'))   # Writes code to HTML file
    file.close()   # Closes HTML file
    sites = pickle.load(open("userdata/" + str(session.get("username")) + ".sites", "rb"))   # Loads a list of the user's sites
    sites.append(str(newid))   # Adds the page to the user's list of pages
    pickle.dump(sites, open("userdata/" + session.get('username') + ".sites", "wb"))   # Saves the sites list
    record.update({str(newid): session.get("username")})   # Updates the master record of sites
    pickle.dump(record, open("pages.data", "wb"))   # Saves the master record of sites
    return render_template('return.html', ID=newid, site_url=site_url)   # Returns a page with the user's new page info


@app.route("/edit/<postid>", methods = ["GET"])
def editget(postid):   # Opens the edit page if the user is authroized to edit the requested page
    try:
        sites = pickle.load(open("userdata/" + str(session.get("username")) + ".sites", "rb"))
        if ((str(postid) in sites) or (session.get('username') in administrators)):   # Checks to see if the user is authroized to edit the page or is an admin
            code = open('templates/userpages/' + str(postid) + '.html', 'r')
            return(render_template("edit.html", pageid = postid, code = (code.read()).decode('utf-8'), username = session.get('username')))
        else:
            return("Access Denied!")
    except:
        return(redirect("/login"))


@app.route("/edit", methods = ["POST"])   # This page deals with updating the pages
def editpost():
    sites = pickle.load(open("userdata/" + str(session.get("username")) + ".sites", "rb"))
    pageid = request.form['pageid']
    if ((pageid in sites) or (session.get('username') in administrators)):
        os.remove('templates/userpages/' + str(pageid) + '.html')   # Removes the old page
        file = open('templates/userpages/' + str(pageid) + '.html', 'w')   # Opens a new file for the page
        file.write(request.form["code"].encode('utf-8'))   # Writes the new code to the new key file
        file.close()   # Closes the key file
        return render_template('return.html', ID=pageid, site_url=site_url)   # Returns a page with the user's new page info
    else:
        return("Access Denied!")

@app.route("/manage", methods = ["GET"])   # Loads the admin page or management page based on user rights
def manage():
    try:
        sites = pickle.load(open("userdata/" + str(session.get("username")) + ".sites", "rb"))
        if session.get('username') not in active:
            active.append(session.get('username'))
        if session.get('username') in administrators:
            return(render_template("admin.html", sites = record, my_sites = sites, username = session.get("username")))
        return(render_template("manager.html", sites = sites, username = session.get("username")))
    except:
        return(redirect("/login"))


@app.route('/p/<ID>', methods=['GET'])    # This section deals with GET requests for user pages
def getPage(ID):
    if os.path.isfile('templates/userpages/' + str(ID).lower() + '.html'):   # Checks to see if the requested page exists
        return(render_template('userpages/' + str(ID).lower() + '.html'))   # The ID section of the request is converted to lower case
    else:   # Returns a 404 if the page does not exist
        return'Error 404: The requested page does not exist!'

@app.route("/delete/<ID>", methods = ["GET"])
def deletePageGet(ID):
    return(render_template("confirmdelete.html", x = ID, username = session.get('username')))


@app.route("/confirmeddelete/<ID>", methods = ["GET"])   # Deletes the page that is requested for deletion
def deletePage(ID):
    if session.get('username') in active:
        sites = pickle.load(open("userdata/" + str(session.get("username")) + ".sites", "rb"))
        if str(ID) in sites:   # Checks to see if the user is authorized to delete the page
            sites.remove(str(ID))
            os.remove('templates/userpages/' + str(ID) + '.html')
            pickle.dump(sites, open("userdata/" + session.get('username') + ".sites", "wb"))
            del record[str(ID)]
            pickle.dump(record, open("pages.data", "wb"))
            return(redirect("/manage"))
        elif session.get('username') in administrators:
            sites = pickle.load(open("userdata/" + record[str(ID)] + ".sites", "rb"))
            sites.remove(str(ID))
            os.remove('templates/userpages/' + str(ID) + '.html')
            pickle.dump(sites, open("userdata/" + record[str(ID)] + ".sites", "wb"))
            del record[str(ID)]
            pickle.dump(record, open("pages.data", "wb"))
            return(redirect("/manage"))
        else:
            return("Access Denied!")
    else:
        return(redirect("/login"))


@app.route("/changepass", methods = ["GET"])   # Serves the change password page if the user is logged in
def changepassGet():
    if session.get('username') in active:
        return(render_template("changepassword.html", username = session.get('username')))
    else:
        return(redirect("/login"))


@app.route("/changepass", methods = ["POST"])   # Works similar to the registration page, but only needs the password
def changepassPost():
    if session.get('username') in active:
        password = request.form["password"]
        password2 = request.form["confirm_password"]
        if password != password2:
            return("The Passwords Entered Do Not Match!")
        else:
            salt = bcrypt.gensalt(14)
            hashedPassword = str(bcrypt.hashpw(str(password), salt))
            pickle.dump(salt, open("userdata/" + session.get('username') + ".salt", "wb"))
            pickle.dump(hashedPassword, open("userdata/" + session.get('username') + ".password", "wb"))
            return(redirect("/manage"))
    else:
        return(redirect("/login"))


app.secret_key = os.urandom(2048)   # Generates a random key for the session cookies
while True:
    try:
        app.run(debug=False)   # Starts the Flask server with debugging set to False
    except:
        print("Error!")
