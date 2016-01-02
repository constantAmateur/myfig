# myfig

## What is it?

I wrote myfig to provide me with a way to easily upload figures that I created to a webspace I own, from which I can share it securely with people of my choosing by sending them a link.  

But there's already much better services like plot.ly, yours looks like crap in comparison, why bother?

Plot.ly (and alternatives) are great, but require you to do some combination of:

 - Learn a new plotting "language".
 - Send your plots to someone else's servers.
 - Pay to keep your plots private and share them privately.
 - Other annoyances I haven't picked up on?

So myfig is for the niche audience who (like me):

 - Have their own web server (or aren't scared by the prospect of running one).
 - Want to keep the plots they create on machines they control.
 - Want to continue using whatever plotting library they're familiar with.
 - Want to share plots by just sending a link.
 - Would like an easily accessible online record of the figures they produce.

## Installation

myfig has two parts. The server, which runs on the machine you want to store your plots on and serve those plots to others over the internet.  The client, which runs on the machine you create plots on and sends them to the server.

### Setting up the server

The first thing you should do is to checkout the git repository with:

    git clone https://github.com/constantAmateur/myfig.git

myfig is written in the python microframework Flask and so requires the python flask module (and the flask-login module) to work.  The passlib module is also needed.  The recommended way to deal with these dependencies is to create a virtual machine in the myfig directory, activate it and ensure the dependencies are installed.

    cd myfig
    virtuanenv venv
    source venv/bin/activate
    pip install flask flask-login passlib

Before running myfig for the first time, you must also configure the application by copying config.py.example to config.py and setting the values to something that makes sense for you (see the comments in config.py).  After you have done this, type

    python application.py

and your plots will be served from http://localhost:5000/.  If you're using myfig regularly, you'll probably want to set it up to be served with something like nginx and uwsgi, but I'll leave that out until such a time as anyone actually asks for it.

### Setting up the client

To use the client, simply import myfig from client in python by putting client.py on your PYTHONPATH or by changing to the directory where client.py is located and then running

    import myfig from client

Then once you've created a plot in matplotlib, save it to the server by running

    myfig('/myplots/or/whatever/cool_figure.png')

you will be asked for the host where myfig is located (so http://localhost:5000/ if you're running on the same machine and serving myfig as described above) and an API key.  For now the API key is just the hashed version of your password stored in config.py on the server.

These credentials can be saved to ~/myfig.conf to prevent having to enter them every time you save a plot.  Your new plot will now be visible at http://localhost:5000/myplots/or/whatever/!


