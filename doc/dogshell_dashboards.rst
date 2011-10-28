Dashboards
==========

Dog allows you to manipulate custom dashboards from the commandline. This does
*not* include automatically generated host-metrics dashboards (but does include
any cloned copies of them). If you're using it interactively, you'll often want
to use `dog`'s `--pretty` option. This will format the JSON in a way that is
properly indented and easy to read. Passing the `--raw` flag will  cause dog to
always return a JSON response as a single line. If you do not specify one of
these, `dog` will by default output either a  tab-delimited CSV format for
simpler data, or a single-line JSON blob for more complex data.

View Dashboards
---------------

By default `show_all` will return a tab-delimited list all custom dashboards for
your organization. The first column are IDs, the second are where the resource
can be accessed via our REST API, then the title, and then the descriptions::

    $ dog dashboard show_all
    1007    /api/v1/dash/1007   Redis (staging)     Watching Redis in staging
    1010    /api/v1/dash/1010   Postgres (staging)  Overall metrics for postgres in staging.
    1011    /api/v1/dash/1011   Postgres (prod)     Overall metrics for postgres in prod.

The pretty version is indented JSON. Using the `--raw` option will give you the
same JSON on a single line::
    
    $ dog --pretty dashboard show_all
    {
      "dashes": [
        {
          "description": "Watching Redis in staging",
          "id": "1007",
          "resource": "/api/v1/dash/1007",
          "title": "Redis (staging)"
        },
        {
          "description": "Overall metrics for postgres in staging.",
          "id": "1010",
          "resource": "/api/v1/dash/1010",
          "title": "Postgres (staging)"
        },
        {
          "description": "Overall metrics for postgres in prod.",
          "id": "1011",
          "resource": "/api/v1/dash/1011",
          "title": "Postgres (prod)"
        }
      ]
    }

To view a specific dashboard, use `dog dashboard show [dashboard id]` For 
example::

    $ dog --pretty dashboard show 1050
    {
      "dash": {
        "description": "A sample dashboard capturing load and CPU.",
        "graphs": [
          {
            "definition": {
              "events": [
                {
                  "q": "events{web}"
                }
              ],
              "requests": [
                {
                  "q": "system.load.1{web}by{host}"
                }
              ]
            },
            "title": "1-min Load (by host)"
          },
          {
            "definition": {
              "events": [
                {
                  "q": "events{env:staging}"
                }
              ],
              "requests": [
                {
                  "q": "system.cpu.user{env:staging} by {host}"
                }
              ],
              "viz": "timeseries"
            },
            "title": "CPU in the environment"
          }
        ],
        "id": 1050,
        "title": "Web Performance CI",
      },
      "resource": "/api/v1/dash/1050",
      "url": "/dash/dash/1050"
    }

This returns a JSON string (indented if you used `--pretty`) with all
information regarding this dashboard. Dashboards are made up of one or more
graphs, whose definitions will also be displayed. For more information about
graph definitions and how they work, please see DataDog's
`Graph Primer <http://help.datadoghq.com/kb/graphs-dashboards/graph-primer>`_

Edit Dashboards
---------------

Create
******

Update
******

Delete
******

Manage from Local Files
-----------------------

To make managing dashboards easier, `dog` also allows you to push and pull 
dashboards between the server and local files. Please note that there is no
ability to merge or do conflict resolution. When you pull, you are overwriting
your local file with whatever is on the server. When you push, you are 
overwriting the server's version with your local file.

Examples for the Impatient
**************************

Pull all your custom dashboards from the server and download them to a 
directory::

    $ dog dashboard pull_all ./my_dashboards

Pull a single dashboard (in this case with ID=1000) from the server to a file::

    $ dog dashboard pull 1000 ./my_dashboard.json

Update a server's dashboard from a dashboard file::

    $ dog dashboard push ./my_dashboard.json

Check out the dashboard in a web browser to see if it looks like you expect::

    $ dog dashboard web_view ./my_dashboard.json

Create a new dashboard file skeleton::

    $ dog dashboard new_file ./another_dashboard.json


Getting Started
***************

If you already have custom dashboards that you've added via DataDog's web 
interface, you can download those to a local directory. Please remember that 
this will only download custom dashboards that you've cloned or created. It will
not download the read-only host dashboards. Invoke it like::

    $ dog dashboard pull_all ./my_dashboards
    1000 /Users/me/my_project/my_dashboards/prod_cassandra.json
    1002 /Users/me/my_project/my_dashboards/redis_staging.json
    1007 /Users/me/my_project/my_dashboards/redis_staging-1007.json
    1009 /Users/me/my_project/my_dashboards/web_staging.json
    1010 /Users/me/my_project/my_dashboards/postgres_staging.json

Dog will create file names based on titles, and will append dashboard IDs if
there are naming conflicts.

Once the files have downloaded, you should add them to your version control 
repository. We recommend that you treat these files as the canonical source of
dashboard definitions from this point forward, and that you automate jobs to
push from your repository to the DataDog server (explained below). Again, 
because `dog` does not know how to merge changes, it will blindly overwrite 
the server version or your local version when you push or pull, respectively.

If you only wish to manage a subset of your dashboards in this manner, we
recommend that you clearly mark them by some convention (either in the title or
description), so that your users do not make manual changes to dashboards that
are later wiped out when you push from your code repo. The `dog` script does not
differentiate between dashboards that are updated through the API vs. the ones
that are updated manually.

Pushing Updates
***************

Adding New Dashboards
*********************
Via both new_file and pulling something someone created on the server.

Viewing Your Changes
********************

Deleting Files
**************

















































