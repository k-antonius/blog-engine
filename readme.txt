*******************************************************************************
Multi-User Blog Engine Udacity Project
Author: Kenneth LaMantia
Last Updated: 6/24/2017
*******************************************************************************
This is a backend for a multi-user blog web application written in Python
that supports the creation of blog posts,
and allows users to comment on or 'like' those posts etc.

There is essentially no front-end code or styling on this project. This is
intentional. Because the backend is a RESTful API, it would be relatively easy
to add front end code.

Installation instructions:

A. To view the project running live:
  A demo is running at 'https://udacity-blog-167512.appspot.com/blog/display/home'. Please
  follow the link to test the app.

B. To develop or run the project locally:

  (1) Dependecies:
    - Python 2.7xx https://www.python.org/downloads/
    - Google App Engine (GAE) https://cloud.google.com/appengine/docs/standard/python/download
    - Webapp2 a python framework for GAE https://webapp2.readthedocs.io/en/latest/index.html
      (should be included in the GAE SDK by default)
    - Jinja 2, a template engine http://jinja.pocoo.org/docs/2.9/intro/#installation
    - Download and install the dependencies following the instructions at the
      links provided.
  (2) Getting the source code
    - Clone this repository (requires Git) or download the code
  (3) To run the project from the terminal
    - Navigate to the directory where you cloned or downloaded the source files.
    - This is the directory containing the "app.yaml" file.
    - Run dev_appserver.py from from this location, by running the command
    "dev_appserver.py app.yaml" in the terminal.
    - Open a web browser and navigate to localhost:8080/blog/signup/display to
    see the project running on the local development server
  (4) Recommended, but not necessary:
    - If you're going to develop this application further, use Eclipse to run
    the app. Follow the instructions at:
    https://cloud.google.com/appengine/docs/standard/python/tools/setting-up-eclipse
    - This requires the Eclipse IDE and its Pydev plugin.
