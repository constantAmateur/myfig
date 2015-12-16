from flask import Flask
from flask import request
from flask import abort
from flask import render_template,url_for,redirect
from flask import send_from_directory
from flask.ext.login import LoginManager, login_required, UserMixin, login_user, logout_user
from werkzeug import secure_filename
from passlib.hash import sha256_crypt as pwhash
import os, json
import socket
from datetime import datetime as dt
app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
app.config['UPLOAD_FOLDER'] = '/home/myoung/tmp/myfig/'
app.config['OBJECT_SUFFIX'] = '.frag'
app.config['SECRET_KEY'] = 'hipohopopotomus'
app.config['USERS']= { 'matt': '$5$rounds=535000$WcOhVvXkz94KQXr5$Iy7SLHFvrBYC5fK8N4Wm88zOHsF5nz45S0KRkn8fB2C'}
app.debug = True

def get_host(ip):
  try:
    tmp=socket.gethostbyaddr(ip)[0]
  except:
    tmp='Unknown'
  return '%s (%s)'%(tmp,ip)

def valid_payload(uploaded):
  if uploaded is None:
    return False
  if 'figure' not in uploaded: 
    return False
  return True

class Figure(object):
  '''
  A figure object is a collection of a figure, some metadata and some code.
  '''
  def __init__(self,tgt):
    self.target = tgt
    self.file_target = os.path.join(app.config['UPLOAD_FOLDER'],tgt)
    self.name = os.path.basename(tgt)
    self.ftype = os.path.splitext(self.name)[1]
    self.load_object()
    #Make certain metadata objects first class objects
    self.cdate = self.mdata['server']['cdate']

  def load_object(self):
    if os.path.exists(self.file_target+'.figure'):
      self.fig = self.name+'.figure'
      self.fig_fh = open(self.file_target+'.figure','rb')
    else:
      raise ValueError('Figure not found.')
    if os.path.exists(self.file_target+'.mdata'):
      self.mdata = json.load(open(self.file_target+'.mdata'))
    else:
      raise ValueError('Metadata not found.')
    if os.path.exists(self.file_target+'.code'):
      self.code = self.name+'.code'
    else:
      self.code = None
 

def get_object(tgt):
  '''
  Check if the figure object exists on this file system.
  If it does, return the tuple of filenames representing
  the figure, metadata and code
  '''
  try:
    return Figure(tgt)
  except:
    return None

@app.route('/ping')
@login_required
def pong():
  return 'pong'

@app.route('/', defaults={'path':''},methods=['POST','GET'])
@app.route('/<path:path>',methods=['POST','GET'])
#@login_required
def explicit(path):
  #Serve the specific object if it's there
  print request,path
  #Check that it's not one of the protected file types.  In production this should be handled by nginx and we should never see these.  But for testing...
  if path[-7:]=='.figure' or path[-6:]=='.mdata' or path[-5:]=='.code':
    return send_from_directory(app.config['UPLOAD_FOLDER'],path)
  if request.method == 'POST':
    print 'Using post'
    print request.files
    #A valid payload consists of three files, (figure,code,metadata)
    uploaded = request.files
    print request.files.keys()
    if valid_payload(uploaded):
      #Figure is mandetory, metadata and code are optional
      figure = uploaded['figure']
      print figure
      #Load the metadata, convert it into a dictionary
      mdata = uploaded.get('mdata')
      mdata = json.loads(mdata.read()) if mdata is not None else {}
      print mdata
      #Code is completely optional
      code = uploaded.get('code')
      print code
      #Add any extra metadata
      mdata = {'server':{},'client':mdata}
      mdata['server']['cdate']=str(dt.now())
      mdata['server']['uploaded_names']={'figure':figure.filename,
              'mdata':uploaded['mdata'].filename if 'mdata' in uploaded else None,
              'code':code.filename if code is not None else None,
              'source':get_host(request.remote_addr)}
      print mdata
      #Create storage names for all the files
      fnom = secure_filename(figure.filename)
      print 'Secure name is...'
      #Where to save?
      tgt = os.path.join(path,fnom)
      ftgt = os.path.join(app.config['UPLOAD_FOLDER'],path,fnom)
      print tgt
      #Create directory if needed
      if not os.path.exists(os.path.dirname(ftgt)):
        os.makedirs(os.path.dirname(ftgt))
      #Get the first non-colliding object name for this path
      orig=tgt
      i=1
      print 'About to enter infinite loop...'
      while get_object(tgt) is not None:
        print tgt
        tgt=orig+'.%d'%i
        i=i+1
      if i!=1:
        fnom = fnom +'%d'%i
      print 'Unambiguous target is...'
      print fnom,tgt
      #Now save things
      figure.save(ftgt+'.figure')
      print 'saved figure'
      f=open(ftgt+'.mdata','wb')
      f.write(json.dumps(mdata))
      f.close()
      print 'metadata saved'
      if code:
        code.save(ftgt+'.code')
      return 'Uploaded'
    else:
      return 'Invalid payload.'
  elif request.method == 'GET':
    tgt = path
    ftgt = os.path.join(app.config['UPLOAD_FOLDER'],path)
    print tgt
    if os.path.isdir(ftgt):
      #Get figure objects in this directory
      figures = [x[:-7] for x in os.listdir(ftgt) if x[-7:]=='.figure']
      figures = [get_object(os.path.join(tgt,x)) for x in figures]
      figures = [x for x in figures if x is not None]
      print figures
      return render_template('figures.html',figures=figures)
    elif get_object(tgt) is not None:
      return render_template('figures.html',figures=[get_object(tgt)])
    else:
      abort(404)

######
#AUTH#
######

class User(UserMixin):
  def __init__(self,user,password):
    self.id = user
    self.password = password

  def is_active(self):
    return True

  def is_authenticated(self):
    return True

  def is_anonymous(self):
    return False

#For now, use hash of password as the API KEY
app.config['API_KEYS'] = dict([(v,User(k,v)) for k,v in app.config['USERS'].iteritems()])

@login_manager.user_loader
def load_user(uid):
  if uid in app.config['USERS']:
    return User(uid,app.config['USERS'][uid])
  return None

@login_manager.request_loader
def load_user_from_request(request):
  api_key = request.args.get('api_key')
  if api_key:
    return app.config['API_KEYS'].get(api_key)
  return None

 
@app.route('/login', methods=['GET','POST'])
def login():
  if request.method == 'GET':
    return render_template('login.html')
  elif request.method == 'POST':
    #Validate login before proceeding
    username = request.form['email']
    password = request.form['pw']
    if username in app.config['USERS'] and pwhash.verify(password,app.config['USERS'][username]):
      user = User(username,password)
      login_user(user)
      forward = request.args.get('next')
      print forward
      #if not next_is_valid(forward):
      #  return abort(400)
      return redirect(forward or url_for('default'))
  return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
  logout_user()
  return redirect(url_for('login'))

if __name__ == '__main__':
  app.run()
