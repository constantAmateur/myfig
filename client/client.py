from StringIO import StringIO
from configobj import ConfigObj
import json
import requests
import os
import tempfile
try:
  import mpld3
  can_html=True
except ImportError:
  print 'Could not load mpld3, to save to interactive html, please first install mpld3.'
  can_html=False
from matplotlib import pyplot as plt

#Load the config file
config=None
for loc in os.curdir,os.path.expanduser('~'),'/etc/myfig',os.environ.get('MYFIG_CONFIG'):
  if loc is None:
    continue
  try:
    config = ConfigObj(os.path.join(loc,'myfig.conf'),raise_errors=True,file_error=True)
    break
  except IOError:
    pass

#Create a config file in home folder if none exists
if config is None:
  config = ConfigObj(os.path.expanduser('~/myfig.conf'))

def validate_host(host,api_key):
  #Try and connect to the host and get a sensible resopnose
  try:
    ret = requests.get(host+'/ping',params={'api_key':api_key},verify=False)
    if getattr(ret,'content','') == 'pong':
      return True
    return False
  except:
    return False

def get_history():
  try:
    #Get a temporary name to use
    with tempfile.NamedTemporaryFile() as tf:
      nom = tf.name
    get_ipython().magic('history -otf %s'%nom)
    return nom
  except:
    return None


def myfig(target,src=None,caption='Created by myfig python client.',format=None,code=None,**kw):
  '''
  target is where it should go on the server, starting with the root /
  src is the figure to save, default to plt.gcf()
  caption should be obvious
  format is the format to save the figure in.  Try to guess from extension if missing
  code is the name of a file containing the code to make the figure.  If none, we attempt to save the current session output.
  Additional keywords are passed to the saving routines (savefig,fig_to_html,...).
  '''
  #Check that we can connect to host
  host = config.get('host','')
  key = config.get('api_key','')
  save = False
  while not validate_host(host,key):
    #Prompt user for valid credentials
    print 'Unable to connect to %s with api key %s'%(host,key)
    host = raw_input('Enter URL where myfig server is located: ')
    key = raw_input('Enter myfig server API key: ')
    config['host'] = host.strip('/')
    config['api_key'] = key
    save = True
  #If we eventually got credentials that work, save them to the config file
  if save:
    config.write()
  #Now do the procesing of the figure
  base,ext = os.path.splitext(target)
  if format is None:
    if len(ext)>1:
      format = ext[1:]
    else:
      raise ValueError('No valid format could be inferred.')
  if src is None:
    src=plt.gcf()
  tmpf = StringIO()
  if format=='html':
    if not can_html:
      raise ValueError('Saving to html requires the mpld3 package.  Please install it, or save using a different format.')
    tmpf.write(mpld3.fig_to_html(src))
  else:
    ret = src.savefig(tmpf,format=format,**kw)
  #Create metadata object and add any metadata
  md = {}
  md['caption']=caption
  #Save it to a "file"
  mdf = StringIO()
  mdf.write(json.dumps(md))
  #Rewind to start...
  tmpf.seek(0)
  mdf.seek(0)
  #Send to remote, trying to save current history as code
  if code is None:
    code = get_history()
  send_to_server(target,tmpf,mdf,code)

def send_to_server(target,fig,md,code=None):
  #Where to send
  endpoint = os.path.dirname(target)
  if endpoint[-1]!='/':
    endpoint = endpoint + '/'
  #The files dictionary needs objects in the format 'destination':(Filename,connection,content_type,headers)
  files = {'figure':(os.path.basename(target),fig),'mdata':md}
  if code is not None:
    files['code'] = open(code,'rb')
  #Now curl them off
  ret = requests.post(config['host']+endpoint,files=files,params={'api_key':config['api_key']},verify=False)
  #Kill code temporary file if it exists
  if code is not None:
    files['code'].close()
    os.unlink(code)
  return ret

