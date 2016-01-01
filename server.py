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
        if c.execute("SELECT * FROM users WHERE username = '" + username + "'") == 1:   # Checks to see of the username exists
            connection.close()
            c.close()
            return(render_template("register.html", error=3))
        else:
            salt = bcrypt.gensalt(14)   # Generates the password salt
            hashedPassword = str(bcrypt.hashpw(str(password), salt))   # Hashes the password
            c.execute("INSERT INTO users VALUES ('" + str(username) + "', '" + hashedPassword + "', '" + salt + "');")
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
                    c.execute("INSERT INTO sites VALUES ('" + postID + "', '" + session.get('username') + "');")
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
    if c.execute("SELECT * FROM users WHERE username = '" + username + "'") == 1:   # Checks to see if the user exists
        c.execute("SELECT * FROM users WHERE username = '" + username + "' LIMIT 1;")
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
    return(render_template("new.html", site_url = site_url, username = session.get('username')))


@app.route("/create", methods = ["POST"])
def createpost():
    if session.get('username') not in active:   # Checks to see if the user is logged in
        return('Please Login to Create a Page')
    customlink = str(request.form['customlink']).lower()   # Gets the custom page name (Optional when first posting a site)
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
    c.execute("INSERT INTO sites VALUES ('" + str(newid) + "', '" + session.get('username') + "');")
    connection.commit()
    c.close()
    connection.close()
    return render_template('return.html', ID=newid, site_url=site_url, username = session.get('username'))   # Returns a page with the user's new page info


@app.route("/edit/<postid>", methods = ["GET"])
def editget(postid):   # Opens the edit page if the user is authroized to edit the requested page
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    try:
        if (c.execute("SELECT id FROM sites WHERE owner = '" + session.get('username') + "' AND id = '" + postid + "';")) == 1 or (session.get('username') in administrators):   # Checks to see if the user is authroized to edit the page or is an admin
            code = open('templates/userpages/' + str(postid) + '.html', 'r')
            return(render_template("edit.html", pageid = postid, code = (code.read()).decode('utf-8'), username = session.get('username')))
        else:
            c.close()
            connection.close()
            return("Access Denied!")
    except:
        c.close()
        connection.close()
        return(redirect("/login"))


@app.route("/edit", methods = ["POST"])   # This page deals with updating the pages
def editpost():
    pageid = request.form['pageid']
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    if (c.execute("SELECT id FROM sites WHERE owner = '" + session.get('username') + "' AND id = '" + pageid + "';")) == 1 or (session.get('username') in administrators):
        os.remove('templates/userpages/' + str(pageid) + '.html')   # Removes the old page
        file = open('templates/userpages/' + str(pageid) + '.html', 'w')   # Opens a new file for the page
        file.write(request.form["code"].encode('utf-8'))   # Writes the new code to the new key file
        file.close()   # Closes the key file
        c.close()
        connection.close()
        return render_template('return.html', ID=pageid, site_url=site_url, username = session.get('username'))   # Returns a page with the user's new page info
    else:
        c.close()
        connection.close()
        return("Access Denied!")

@app.route("/manage", methods = ["GET"])   # Loads the admin page or management page based on user rights
def manage():
    connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
    c = connection.cursor(pymysql.cursors.DictCursor)
    error = session.get('error')
    session.pop('error', None)
    c.execute("SELECT id FROM sites WHERE owner = '" + session.get('username') + "';")
    sites = [item['id'] for item in c.fetchall()]
    if session.get('username') not in active:
        active.append(session.get('username'))
    if session.get('username') in administrators:
        c.execute("SELECT id FROM sites LIMIT 1000;")   # Limited for now until we get a next page button
        record = [item['id'] for item in c.fetchall()]
        c.close()
        connection.close()
        return(render_template("admin.html", error=error, sites = record, my_sites = sites, username = session.get("username")))
    return(render_template("manager.html", error=error, sites = sites, username = session.get("username")))


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
        connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
        c = connection.cursor(pymysql.cursors.DictCursor)
        if (c.execute("SELECT id FROM sites WHERE owner = '" + session.get('username') + "' AND id = '" + ID + "';")) == 1 or session.get('username') in administrators:   # Checks to see if the user is authorized to delete the page
            c.execute("DELETE FROM sites WHERE id = '" + ID + "';")
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
        password = request.form["password"]
        password2 = request.form["confirm_password"]
        if password != password2:
            return(render_template('changepassword.html', username=session.get('username'), error=1))
        if password == '':
            return(render_template('changepassword.html', username=session.get('username'), error=2))
        else:
            connection = pymysql.connect(host=sqlhost,
                             user=sqluser,
                             password=sqlpass,
                             db=sqldb,
                             charset=sqlcharset,
                             cursorclass=pymysql.cursors.DictCursor)
            c = connection.cursor(pymysql.cursors.DictCursor)
            salt = bcrypt.gensalt(14)
            hashedPassword = str(bcrypt.hashpw(str(password), str(salt)))
            c.execute("UPDATE users SET password = '" + hashedPassword + "', salt = '" + salt + "' WHERE username = '" + session.get('username') + "';")
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