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
import humanize
app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
app.config.from_object('config')

def get_host(ip):
  try:
    tmp=socket.gethostbyaddr(ip)[0]
    return '%s (%s)'%(tmp,ip)
  except:
    return '(%s)'%ip

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
    print 'Target is %s'%tgt
    print 'Config dir is %s'%app.config['UPLOAD_FOLDER']
    self.target = tgt
    self.file_target = os.path.join(app.config['UPLOAD_FOLDER'],tgt)
    print 'File target is %s'%self.file_target
    self.name = os.path.basename(tgt)
    self.ftype = os.path.splitext(self.name)[1]
    self.load_object()
    #Get the route for this object
    self.route = os.path.relpath(self.file_target,app.config['UPLOAD_FOLDER'])
    if self.route == '.':
      self.route = '/'
    #Make certain metadata objects first class objects
    self.cdate = dt.strptime(self.mdata['server']['cdate'],"%Y-%m-%d %H:%M:%S.%f")
    #self.cdate = self.mdata['server']['cdate']

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

  def human_time(self):
    return humanize.naturaldelta(dt.now()-self.cdate)

 
class Directory(object):
  '''
  A folder.
  '''
  def __init__(self,path,include_subdirs=True):
    self.path = path
    self.ls = os.listdir(path)
    figures = [x[:-7] for x in self.ls if not os.path.isdir(x) and x[-7:]=='.figure']
    figures = [get_object(os.path.join(path,x)) for x in figures]
    figures = [x for x in figures if x is not None]
    self.figures = figures
    self.cdate = max([x.cdate for x in figures]) if len(figures)!=0 else None
    self.count = len(self.figures)
    self.route = os.path.relpath(path,app.config['UPLOAD_FOLDER'])
    if self.route == '.':
      self.route = '/'
    self.url = url_for('explicit',path=self.route)
    #Add trailing slash for good measure
    if self.url[-1] != '/':
      self.url =self.url +'/'
    print self.route,self.url
    self.dirs=[]
    if include_subdirs:
      print path,self.ls
      tmp = [os.path.join(path,x) for x in self.ls if os.path.isdir(os.path.join(path,x))]
      print tmp
      for d in tmp:
        dd=Directory(d)
        dd.name=os.path.relpath(d,self.path)
        #Update the most recently modified date to be the max of all sub-folders
        if dd.cdate > self.cdate:
          self.cdate = dd.cdate
        #Add in the count for figures in sub-directories
        self.count += dd.count
        self.dirs.append(dd)

  def calculate_crumbs(self):
    '''
    Returns a list of the elements and their urls
    '''
    dirs = [ x for x in self.route.split('/') if x!='']
    out = []
    for i,dd in enumerate(dirs):
      out.append([dd,'/'.join(['']+dirs[:i+1]+[''])])
    return out

  def human_time(self):
    return humanize.naturaldelta(dt.now()-self.cdate)
 

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

def list_dir(path,include_subdirs=True):
  '''
  Gets all the figure objects in this directory and the number
  of figure objects in subdirectories
  '''
  ls = os.listdir(path)
  print 'HELLO EVERYBODY!',ls
  figures = [x[:-7] for x in ls if not os.path.isdir(x) and x[-7:]=='.figure']
  figures = [get_object(os.path.join(path,x)) for x in figures]
  figures = [x for x in figures if x is not None]
  print figures,include_subdirs
  #Want to return a tuple of (name,num_figs,most_recent_addition) for each directory
  dirs=[]
  if include_subdirs:
    print path,ls
    tmp = [os.path.join(path,x) for x in ls if os.path.isdir(os.path.join(path,x))]
    print tmp
    for d in tmp:
      print d
      count = 0
      mod = 0
      for dir,subdir,files in os.walk(d):
        fig_files = [x[:-7] for x in files if x[-7:]=='.figure']
        fig_files = [get_object(os.path.join(dir,x)) for x in fig_files]
        fig_files = [x for x in fig_files if x is not None]
        count += len(fig_files)
        mod = max(mod,max([0]+[os.stat(os.path.join(dir,x.fig)).st_mtime for x in fig_files]))
      print count,mod
      dirs.append((d,count,mod))
  return dirs+figures

#@app.route('/static/<path:path>')
#def static(path):
#  return send_from_directory('static',path)

@app.route('/ping')
@login_required
def pong():
  return 'pong'

@app.route('/', defaults={'path':''},methods=['POST','GET'])
@app.route('/<path:path>',methods=['POST','GET'])
@login_required
def explicit(path):
  #if not current_user.is_authenticated:
  #  return current_app.login_manager.unauthorized()
  #Serve the specific object if it's there
  print "We're making a request for a path object."
  print request,path,request.method
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
      mdata['server']['cdate']=dt.now()
      mdata['server']['user']=current_user.id
      mdata['server']['source'] = get_host(request.remote_addr)
      mdata['server']['uploaded_names']={'figure':figure.filename,
              'mdata':uploaded['mdata'].filename if 'mdata' in uploaded else None,
              'code':code.filename if code is not None else None
              }
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
      #If it's a directory, should end in a slash, redirect if it doesn't
      if path=='' or path[-1]!='/':
        print 'Missing trailing slash on directory, redirecting...'
        redirect(url_for('explicit',path=path+'/',**request.args))
      #Get figure objects in this directory
      listing = Directory(ftgt,True)
      print listing
      print listing.calculate_crumbs()
      return render_template('directory.html',listing=listing,crumbs=listing.calculate_crumbs())
    elif get_object(tgt) is not None:
      return render_template('figure.html',figure=get_object(tgt))
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
  print request.url
  print request.referrer
  if request.method == 'GET':
    return render_template('login.html',next=request.args.get('next'))
  elif request.method == 'POST':
    #Validate login before proceeding
    print request.form
    username = request.form['user']
    password = request.form['pw']
    if username in app.config['USERS'] and pwhash.verify(password,app.config['USERS'][username]):
      user = User(username,password)
      login_user(user)
      print request.args
      forward = request.form.get('next')
      print forward
      #if not next_is_valid(forward):
      #  return abort(400)
      return redirect(forward or url_for('explicit'))
      #return redirect('/a/b/c/')
    return redirect(url_for('login',next=request.form['next']))
  return None

@app.route('/logout')
@login_required
def logout():
  logout_user()
  return redirect(url_for('login'))

if __name__ == '__main__':
  app.run()
