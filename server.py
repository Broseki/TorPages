'''
TorPages
---
This server software is used to allow individuals to publish static HTML/Text content to the DeepWeb without
cost.

This software is licensed under the Kopimi concept, meaning this software is essentially public domain,
but it would be nice to refer to CaveFox Telecom and Michael Canning as it is always nice to receive credit
for work.

For more information contact Michael Canning - mcanning(at)cavefox(dot)net

Check out our GitHub repository and consider contributing [https://github.com/mcanningjr/TorPages]
'''

import shutil  # Used to remove directories
from flask import render_template   # Used to render HTML pages
from flask import Flask
from flask import request   # Used to process POST requests
from flask import session   # Used to handle logins
from flask import redirect   # Used to handle redirecting
import os   # Used to check for/delete files
import hashlib   # Used to hash the website modification keys
import bcrypt   # Used to encrypt the user passwords
import pymysql
import uuid
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from flask import send_from_directory

app = Flask(__name__)   # Defines Flask Application
sqlhost = '127.0.0.1'
sqluser = 'torpages'
sqlpass = ''
sqldb = 'torpages'
sqlcharset = 'utf8mb4'

site_url = 'http://m54wkp5ctdpummms.onion'
admin_email = 'abuse@cavefox.net'
active = []   # Used to keep a list of logged in users


administrators = ['mcanning']   # Define the administrator accounts


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
    if (username.isalnum() is False or len(username) > 20):
        return(render_template("register.html", error=1))
    if password != password2:
        return(render_template("register.html", error=2))
    if password == '':
        return(render_template("register.html", error=4))
    else:
        connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
        c = connection.cursor(pymysql.cursors.DictCursor)
        if c.execute("SELECT * FROM users WHERE username=%s", username) == 1:   # Checks to see of the username exists
            connection.close()
            c.close()
            return(render_template("register.html", error=3))
        else:
            salt = bcrypt.gensalt(14)   # Generates the password salt
            hashedPassword = str(bcrypt.hashpw(str(password), salt))   # Hashes the password
            c.execute("INSERT INTO users VALUES (%s, %s, %s);", (username, hashedPassword, salt))
            connection.commit()
            session['username'] = username   # Logs the user in
            c.close()
            connection.close()
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
                    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
                    c = connection.cursor(pymysql.cursors.DictCursor)
                    c.execute("INSERT INTO sites VALUES (%s, %s);", (postID, session.get("username")))
                    connection.commit()
                    os.remove("keys/" + str(postID) + '.key')   # Removes the key file
                    session['error'] = 3
                    c.close()
                    connection.close()
                    return(redirect('/manage'))   # Returns a page with the user's new page info
                else:   # Returns an error to the user is the modification key used is invalid
                    return render_template("legacy.html", username=session.get('username'), error=2)
            else:   # Returns an error if the page being modified never existed in the first place
                return render_template("legacy.html", username=session.get('username'), error=1)
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
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    if c.execute("SELECT * FROM users WHERE username = %s", (username)) == 1:   # Checks to see if the user exists
        c.execute("SELECT * FROM users WHERE username = %s LIMIT 1;", (username))
        userdata = c.fetchone()
        hashed = str(bcrypt.hashpw(str(password), str(userdata['salt'])))
        if str(hashed) != str(userdata['password']):   # Verifies the password
            c.close()
            connection.close()
            return(render_template("index.html", admin_email=admin_email, error=1))
        else:
            session.pop('username', None)   # Removes any session that exists
            session['username'] = userdata['username']   # Sets the session
            c.close()
            connection.close()
            return(redirect('/manage'))   # Sends the user to the management page
    else:
        c.close()
        connection.close()
        return(render_template("index.html", admin_email=admin_email, error=1))


@app.route("/logout", methods = ["GET"])   # Logs out the user
def logout():
    try:
        active.remove(session.get('username'))   # Removes the user from the active users list
        session.pop('username', None)   # Closes the user's session
        return(render_template('index.html', error=2, admin_email=admin_email))
    except:
        return(redirect('/'))


@app.route("/create", methods = ["GET"])   # Returns the create a news page page
def createget():
    if not session.get('username'):
        return redirect('/')
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    c.execute("SELECT name FROM subdirs WHERE owner = %s;", session.get('username'))
    sites = [item['name'] for item in c.fetchall()]
    c.close()
    connection.close()
    otk = hash(os.urandom(4096))
    session['key'] = otk
    return(render_template("new.html", key=otk, sites = sites, site_url = site_url, username = session.get('username')))


@app.route("/console", methods = ["GET"])   # Returns the create a news page page
def consoleget():
    if not session.get('username') in administrators:
        return redirect('/')
    return(render_template("console.html", username = session.get('username')))


@app.route("/console", methods = ["POST"])   # Returns the create a news page page
def consolepost():
    if not session.get('username') in administrators:
        return redirect('/')
    site = request.form['site']
    item = request.form['item']
    type = request.form['type']
    otk = hash(os.urandom(4096))
    session['key'] = otk
    if str(type) == "site":
        return(render_template("confirmsitedelete.html", key=otk, site = site, username = session.get('username')))
    if str(type) == "file":
        return(render_template("confirmfiledelete.html", key=otk, realname = item, filename = item, username = session.get('username')))
    if str(type) == "sitepage":
        return(render_template("confirmsitepagedelete.html", key=otk, site = site, page=item, username = session.get('username')))
    if str(type) == "generalpage":
        return(render_template("confirmdelete.html", key=otk, x = item, username = session.get('username')))



@app.route("/create", methods = ["POST"])
def createpost():
    if session.get('username') not in active:   # Checks to see if the user is logged in
        return('Please Login to Create a Page')
    subdir = request.form['subdir']
    customlink = str(request.form['customlink']).lower()   # Gets the custom page name (Optional when first posting a site)
    verkey = session.get('key')
    key = request.form['key']
    session.pop('key', None)
    if not str(key) == str(verkey):
        return('Access Denied!')
    if subdir == 'p':
        sub = "/p/"
        if os.path.isfile('templates/userpages/' + customlink + '.html') and customlink is not '':   # Checks to see if the custom link is taken if one is requested
            return render_template('new.html', code=request.form["code"], username=session.get('username'), error=2)
        newid = uuid.uuid4()   # Generates a new page ID
        while os.path.isfile('templates/userpages/' + str(id) + '.html'):   # Checks to see if the ID is take and creates a new one if it is
            newid = uuid.uuid4()
        if customlink is not '':    # Checks if the user set a custom post ID
            if(customlink.isalnum() is False or len(customlink) > 50):   # Checks custom string for common invalid characters
               return(render_template('new.html', code=request.form["code"], username=session.get('username'), error=1))
            newid = customlink   # Redefines the ID to the custom one if a user chose one
        file = open('templates/userpages/' + str(newid) + '.html', 'w')   # Opens a new HTML file
        file.write(request.form["code"].encode('utf-8'))   # Writes code to HTML file
        file.close()   # Closes HTML file
        connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
        c = connection.cursor(pymysql.cursors.DictCursor)
        c.execute("INSERT INTO sites VALUES (%s, %s);", (str(newid), session.get('username')))
        connection.commit()
        c.close()
        connection.close()
        return render_template('return.html', subdir=sub, ID=newid, site_url=site_url, username = session.get('username'))   # Returns a page with the user's new page info
    else:
        connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
        c = connection.cursor(pymysql.cursors.DictCursor)
        sub = "/s/" + subdir + '/'
        if(c.execute("SELECT %s FROM subdirs WHERE owner = %s;", (subdir, session.get('username')))):
            if os.path.isfile('templates/dirs/' + subdir + '/' + customlink + '.html') and customlink is not '':   # Checks to see if the custom link is taken if one is requested
                return render_template('new.html', code=request.form["code"], username=session.get('username'), error=2)
            newid = uuid.uuid4()   # Generates a new page ID
            while os.path.isfile('templates/dirs/' + subdir + '/' + str(id) + '.html'):   # Checks to see if the ID is take and creates a new one if it is
                newid = uuid.uuid4()
            if customlink is not '':    # Checks if the user set a custom post ID
                if(customlink.isalnum() is False or len(customlink) > 50):   # Checks custom string for common invalid characters
                    return(render_template('new.html', code=request.form["code"], username=session.get('username'), error=1))
                newid = customlink   # Redefines the ID to the custom one if a user chose one
            file = open('templates/dirs/' + subdir + '/' + str(newid) + '.html', 'w')   # Opens a new HTML file
            file.write(request.form["code"].encode('utf-8'))   # Writes code to HTML file
            file.close()   # Closes HTML file
            c.close()
            connection.close()
            return render_template('return.html', subdir=sub, ID=newid, site_url=site_url, username = session.get('username'))


@app.route("/edit/<postid>", methods = ["GET"])
def editget(postid):   # Opens the edit page if the user is authorized to edit the requested page
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    try:
        if (c.execute("SELECT id FROM sites WHERE owner = %s AND id = %s;", (session.get('username'), str(postid)))) == 1:   # Checks to see if the user is authroized to edit the page or is an admin
            code = open('templates/userpages/' + str(postid) + '.html', 'r')
            otk = hash(os.urandom(4096))
            session['key'] = otk
            return(render_template("edit.html", pageid = postid, key=otk, code = (code.read()).decode('utf-8'), username = session.get('username')))
        else:
            c.close()
            connection.close()
            return("Access Denied!")
    except:
        c.close()
        connection.close()
        return(redirect("/login"))


@app.route("/sites/edit/<site>/<postid>", methods = ["GET"])
def editsitepageget(site, postid):   # Opens the edit page if the user is authorized to edit the requested page
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    try:
        if (c.execute("SELECT name FROM subdirs WHERE owner = %s AND name = %s;", (session.get('username'), str(site)))) == 1 and os.path.isfile('templates/dirs/' + str(site).lower() + '/' + str(postid).lower() + '.html'):   # Checks to see if the user is authroized to edit the page or is an admin
            code = open('templates/dirs/' + str(site).lower() + '/' + str(postid).lower() + '.html', 'r')
            otk = hash(os.urandom(4096))
            session['key'] = otk
            c.close()
            connection.close()
            return(render_template("editsitepage.html", site=site, pageid = postid, key=otk, code = (code.read()).decode('utf-8'), username = session.get('username')))
        else:
            c.close()
            connection.close()
            return("Access Denied!")
    except:
        c.close()
        connection.close()
        return(redirect("/login"))


@app.route("/sites/edit", methods = ["POST"])   # This page deals with updating the pages
def editsitepagepost():
    pageid = request.form['pageid']
    key = request.form['key']
    site = request.form['site']
    verkey = session.get('key')
    session.pop('key', None)
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    if (c.execute("SELECT name FROM subdirs WHERE owner = %s AND name = %s;", (session.get('username'), site)) == 1 and str(verkey) == str(key)):
        os.remove('templates/dirs/' + str(site).lower() + '/' + str(pageid).lower() + '.html')   # Removes the old page
        file = open('templates/dirs/' + str(site).lower() + '/' + str(pageid).lower() + '.html', 'w')   # Opens a new file for the page
        file.write(request.form["code"].encode('utf-8'))   # Writes the new code to the new key file
        file.close()   # Closes the key file
        c.close()
        connection.close()
        return render_template('return.html', subdir='/s/' + site + '/', ID=pageid, site_url=site_url, username = session.get('username'))   # Returns a page with the user's new page info
    else:
        c.close()
        connection.close()
        return("Access Denied!")


@app.route("/edit", methods = ["POST"])   # This page deals with updating the pages
def editpost():
    pageid = request.form['pageid']
    key = request.form['key']
    verkey = session.get('key')
    session.pop('key', None)
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    if (c.execute("SELECT id FROM sites WHERE owner = %s AND id = %s;", (session.get('username'), pageid)) == 1) and str(verkey) == str(key):
        os.remove('templates/userpages/' + str(pageid) + '.html')   # Removes the old page
        file = open('templates/userpages/' + str(pageid) + '.html', 'w')   # Opens a new file for the page
        file.write(request.form["code"].encode('utf-8'))   # Writes the new code to the new key file
        file.close()   # Closes the key file
        c.close()
        connection.close()
        return render_template('return.html', ID='/p/' + pageid, site_url=site_url, username = session.get('username'))   # Returns a page with the user's new page info
    else:
        c.close()
        connection.close()
        return("Access Denied!")


def getfiles(username):
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    c.execute("SELECT filename FROM files WHERE owner = %s;", username)
    filenames = [str(item['filename']) for item in c.fetchall()]
    c.execute("SELECT realname FROM files WHERE owner = %s;", username)
    realnames = [str(item['realname']) for item in c.fetchall()]
    c.close()
    connection.close()
    return(zip(filenames, realnames))


@app.route("/manage", methods = ["GET"])   # Loads the admin page or management page based on user rights
def manage():
    if not session.get('username'):
        return(redirect('/'))
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    error = session.get('error')
    session.pop('error', None)
    c.execute("SELECT id FROM sites WHERE owner = %s;", (session.get('username')))
    sites = [item['id'] for item in c.fetchall()]
    c.execute("SELECT name FROM subdirs WHERE owner = %s;", (session.get('username')))
    subdirs = [item['name'] for item in c.fetchall()]
    directories = []
    for x in subdirs:
        y = os.listdir('templates/dirs/' + x)
        dirfin = []
        for z in y:
            dirfin.append(z[:len(z)-5])
        directories.append({x: dirfin})
    files = getfiles(session.get('username'))
    if session.get('username') not in active:
        active.append(session.get('username'))
        return(render_template("admin.html", error=error, subdirs= subdirs, dirs = directories, files = files, sites = sites, username = session.get("username")))
    return(render_template("manager.html", error=error, subdirs= subdirs, dirs = directories, files = files, sites = sites, username = session.get("username")))


@app.route('/p/<ID>', methods=['GET'])    # This section deals with GET requests for user pages
def getPage(ID):
    if os.path.isfile('templates/userpages/' + str(ID).lower() + '.html'):   # Checks to see if the requested page exists
        return(render_template('userpages/' + str(ID).lower() + '.html'))   # The ID section of the request is converted to lower case
    else:   # Returns a 404 if the page does not exist
        return'Error 404: The requested page does not exist!'


@app.route('/s/<ID>', methods=['GET'])    # This section deals with GET requests for user pages
def getSiteIndex(ID):
    if os.path.isfile('templates/dirs/' + str(ID).lower() + '/index.html'):   # Checks to see if the requested page exists
        return(render_template('dirs/' + str(ID).lower() + '/index.html'))   # The ID section of the request is converted to lower case
    else:   # Returns a 404 if the page does not exist
        return'Error 404: The requested page does not exist!'


@app.route('/s/<ID>/<page>', methods=['GET'])    # This section deals with GET requests for user pages
def getSitePage(ID, page):
    if os.path.isfile('templates/dirs/' + str(ID).lower() + '/' + str(page).lower() + '.html'):   # Checks to see if the requested page exists
        return(render_template('dirs/' + str(ID).lower() + '/' + str(page).lower() + '.html'))   # The ID section of the request is converted to lower case
    else:   # Returns a 404 if the page does not exist
        return'Error 404: The requested page does not exist!'


@app.route("/delete/<ID>", methods = ["GET"])
def deletePageGet(ID):
    otk = hash(os.urandom(4096))
    session['key'] = otk
    return(render_template("confirmdelete.html", key=otk, x = ID, username = session.get('username')))


@app.route("/sites/deletefile/<ID>/<page>", methods = ["GET"])
def deleteSitePageGet(ID, page):
    otk = hash(os.urandom(4096))
    session['key'] = otk
    return(render_template("confirmsitepagedelete.html", key=otk, site = ID, page=page, username = session.get('username')))


@app.route("/sites/deletefile", methods = ["POST"])
def deletePagePost():
    if not session.get('username'):
        return(redirect('/'))
    key = request.form['key']
    site = request.form['site']
    cookey = session.get('key')
    page = request.form['page']
    if not str(key) == str(cookey):
        return(redirect('/manage'))
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    if (c.execute("SELECT name FROM subdirs WHERE owner = %s AND name = %s;", (session.get('username'), site)) and os.path.isfile("templates/dirs/" + site + "/" + page + ".html")) or (session.get('username') in administrators):
        os.remove("templates/dirs/" + site + "/" + page + ".html")
        c.close()
        connection.close()
        session['error'] = 7
        return(redirect('/manage'))
    else:
        c.close()
        connection.close()
        return(redirect("/manage"))


@app.route("/createsite", methods = ["GET"])
def createSiteGet():
    if session.get('username'):
        otk = hash(os.urandom(4096))
        session['key'] = otk
        return(render_template("create_site.html", key=otk, site_url=site_url, username = session.get('username')))
    else:
        return(redirect('/login'))


@app.route("/sites/deletesite", methods = ["POST"])
def deleteSitePost():
    if not session.get('username'):
        return(redirect('/'))
    key = request.form['key']
    site = request.form['site']
    cookey = session.get('key')
    if not str(key) == str(cookey):
        return(redirect('/manage'))
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    if c.execute("SELECT * FROM subdirs WHERE owner = %s AND name = %s;", (session.get('username'), site)) or session.get('username') in administrators:
        shutil.rmtree("templates/dirs/" + site)
        c.execute("DELETE FROM subdirs WHERE name = %s LIMIT 1;", (site))
        connection.commit()
        c.close()
        connection.close()
        session['error'] = 5
        return(redirect('/manage'))
    else:
        c.close()
        connection.close()
        return(redirect("/manage"))


@app.route("/sites/deletesite/<ID>", methods = ["GET"])
def deleteSiteGet(ID):
    otk = hash(os.urandom(4096))
    session['key'] = otk
    return(render_template("confirmsitedelete.html", key=otk, site = ID, username = session.get('username')))


@app.route("/createsite", methods = ["POST"])   # Deletes the page that is requested for deletion
def createSitePost():
    if not session.get('username'):
        return(redirect('/'))
    key = request.form['key']
    verkey = session.get('key')
    session.pop('key', None)
    if session.get('username') in active and str(key) == str(verkey):
        connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
        c = connection.cursor(pymysql.cursors.DictCursor)
        subdir = request.form['subdir']
        if not os.path.exists('templates/dirs/' + subdir):   # Checks to see if the user is authorized to delete the page
            c.execute("INSERT INTO subdirs VALUES (%s, %s);", (str(subdir), session.get('username')))
            connection.commit()
            session['error'] = 6
            c.close()
            connection.close()
            os.mkdir('templates/dirs/' + subdir)
            session['error'] = 6
            return(redirect("/manage"))
        else:
            c.close()
            connection.close()
            otk = hash(os.urandom(4096))
            session['key'] = otk
            return(render_template("create_site.html", key=otk, username = session.get('username'), error = 1))
    else:
        return(redirect("/login"))


@app.route("/deletefile/<ID>", methods = ["GET"])
def deleteFileGet(ID):
    if not session.get('username'):
        return(redirect('/'))
    otk = hash(os.urandom(4096))
    session['key'] = otk
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    filename = ID
    c.execute("SELECT realname FROM files WHERE owner = %s AND filename = %s;", (session.get('username'), filename))
    realname = c.fetchone()['realname']
    return(render_template("confirmfiledelete.html", realname = realname, key=otk, filename = ID, username = session.get('username')))


@app.route("/deletefile", methods = ["POST"])   # Deletes the page that is requested for deletion
def deleteFile():
    if not session.get('username'):
        return(redirect('/'))
    key = request.form['key']
    filename = request.form['file']
    verkey = session.get('key')
    session.pop('key', None)
    if session.get('username') in active and str(key) == str(verkey):
        connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
        c = connection.cursor(pymysql.cursors.DictCursor)
        if (c.execute("SELECT filename FROM files WHERE owner = %s AND filename = %s;", (session.get('username'), filename))) == 1 or session.get('username') in administrators:   # Checks to see if the user is authorized to delete the page
            c.execute("DELETE FROM files WHERE filename = %s;", (filename))
            connection.commit()
            os.remove('static/f/' + str(filename))
            session['error'] = 4
            c.close()
            connection.close()
            return(redirect("/manage"))
        else:
            c.close()
            connection.close()
            return("Access Denied!")
    else:
        return(redirect("/login"))


@app.route("/upload", methods = ["GET"])
def uploadget():
    if not session.get('username'):
        return(redirect('/'))
    otk = hash(os.urandom(4096))
    session['key'] = otk
    return(render_template("upload.html", key=otk, username = session.get('username')))


@app.route("/editfile/<filename>", methods = ["GET"])
def editfileget(filename):
    if not session.get('username'):
        return(redirect('/'))
    otk = hash(os.urandom(4096))
    session['key'] = otk
    return(render_template("editfile.html", filename = filename, key=otk, username = session.get('username')))


@app.route("/editupload", methods = ["POST"])   # This page deals with updating the pages
def fileeditpost():
    if not session.get('username'):
        return(redirect('/'))
    file = request.files['datafile']
    filename = request.form['filename']
    if file.content_length > 31457280:
        otk = hash(os.urandom(4096))
        session['key'] = otk
        return(render_template("upload.html", key=otk, username = session.get('username'), error = 1))
    key = request.form['key']
    verkey = session.get('key')
    session.pop('key', None)
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    if (session.get('username') in active and str(verkey) == str(key)) and (c.execute("SELECT filename FROM files WHERE owner = %s AND filename = %s;", (session.get('username'), filename))):
        os.remove('static/f/' + str(filename))
        file.save(os.path.join('static/f/', filename))
        c.execute("UPDATE files SET realname=%s WHERE filename=%s AND owner=%s LIMIT 1;", (str(file.filename), str(filename), session.get('username')))
        connection.commit()
        c.close()
        connection.close()
        return render_template('return_upload.html', filename=filename, site_url=site_url, username = session.get('username'))   # Returns a page with the user's new page info
    else:
        c.close()
        connection.close()
        return("Access Denied!")


@app.route("/upload", methods = ["POST"])   # This page deals with updating the pages
def uploadpost():
    if not session.get('username'):
        return(redirect('/'))
    file = request.files['datafile']
    if file.content_length > 31457280:
        otk = hash(os.urandom(4096))
        session['key'] = otk
        return(render_template("upload.html", key=otk, username = session.get('username'), error = 1))
    key = request.form['key']
    verkey = session.get('key')
    session.pop('key', None)
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    if (session.get('username') in active and str(verkey) == str(key)):
        uuidx = uuid.uuid4()
        filename = file.filename
        extension = filename.rsplit('.', 1)[1]
        if extension is '.php':
            otk = hash(os.urandom(4096))
            session['key'] = otk
            return(render_template("upload.html", key=otk, username = session.get('username'), error = 2))
        newfilename = str(uuidx) + '.' + extension
        file.save(os.path.join('static/f/', newfilename))
        c.execute("INSERT INTO files VALUES (%s, %s, %s);", (str(newfilename), session.get('username'), str(filename)))
        connection.commit()
        c.close()
        connection.close()
        return render_template('return_upload.html', filename=newfilename, site_url=site_url, username = session.get('username'))   # Returns a page with the user's new page info
    else:
        c.close()
        connection.close()
        return("Access Denied!")


@app.route('/f/<path:path>')
def send_css(path):
    return send_from_directory('static/f', path)


@app.route('/favicon.ico')
def send_favicon():
    return send_from_directory('static/assets', 'favicon.ico')


@app.route("/delete", methods = ["POST"])   # Deletes the page that is requested for deletion
def deletePage():
    key = request.form['key']
    ID = request.form['site']
    verkey = session.get('key')
    session.pop('key', None)
    if session.get('username') in active and str(key) == str(verkey):
        connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
        c = connection.cursor(pymysql.cursors.DictCursor)
        if (c.execute("SELECT id FROM sites WHERE owner = %s AND id = %s;", (session.get('username'), ID))) == 1 or session.get('username') in administrators:   # Checks to see if the user is authorized to delete the page
            c.execute("DELETE FROM sites WHERE id = %s;", (ID))
            connection.commit()
            os.remove('templates/userpages/' + str(ID) + '.html')
            session['error'] = 1
            c.close()
            connection.close()
            return(redirect("/manage"))
        else:
            c.close()
            connection.close()
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
        connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
        c = connection.cursor(pymysql.cursors.DictCursor)
        password = request.form["password"]
        password2 = request.form["confirm_password"]
        currentpassword = request.form['current_password']
        c.execute("SELECT * FROM users WHERE username = %s LIMIT 1;", (session.get('username')))
        userdata = c.fetchone()
        hashed = str(bcrypt.hashpw(str(currentpassword), str(userdata['salt'])))
        if str(hashed) != str(userdata['password']):   # Verifies the password
            c.close()
            connection.close()
            return(render_template('changepassword.html', username=session.get('username'), error=3))
        if password != password2:
            c.close()
            connection.close()
            return(render_template('changepassword.html', username=session.get('username'), error=1))
        if password == '':
            c.close()
            connection.close()
            return(render_template('changepassword.html', username=session.get('username'), error=2))
        else:
            salt = bcrypt.gensalt(14)
            hashedPassword = str(bcrypt.hashpw(str(password), str(salt)))
            c.execute("UPDATE users SET password = %s, salt = %s WHERE username = %s;", (hashedPassword, salt, session.get('username')))
            connection.commit()
            session['error'] = 2
            c.close()
            connection.close()
            return(redirect("/manage"))
    else:
        return(redirect("/login"))


app.secret_key = os.urandom(4096)   # Generates a random key for the session cookies

while True:
    try:
        if __name__ == "__main__":
            http_server = HTTPServer(WSGIContainer(app))
            http_server.listen(5000)
            IOLoop.instance().start()
    except:
        pass