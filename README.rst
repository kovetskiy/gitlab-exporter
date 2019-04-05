**************************
Prometheus Gitlab Exporter
**************************
This uses `Gitlab <https://gitlab.com>`__'s API to fetch some data and exposes
it to `Prometheus <https://prometheus.io/>`__.


Getting Started
===============
Get your personal access token from
``https://git.example.com/profile/personal_access_tokens``

Run with Docker::

    docker run --rm -it \
    -p 3001:3001 \
    -e URL=$YOUR_GITLAB_URL
    -e TOKEN=$YOUR_GITLAB_TOKEN
    kovetskiy/gitlab-exporter

Install from Git
----------------
Install requirements, e.g.::

    pip install -r requirements.txt

Run this::

    ./gitlab_exporter.py

Check metrics::

    curl localhost:3001/metrics


Config
======
The following environment variables may be set::

    LOGLEVEL=INFO PORT=3002 INTERVAL=180 ./gitlab_exporter.py

====================  ===========
Environment Variable  Description
====================  ===========
LOGLEVEL              Standard Python `log level`_
PORT                  Port to listen on
INTERVAL              Interval in seconds to wait between data fetches
URL                   URL to your GitLab installation
TOKEN                 Your personal access token for the GitLab API
====================  ===========

.. _log level: https://docs.python.org/3.5/library/logging.html#levels


Notes
=====
There are efforts for native Prometheus integration in Gitlab, e.g.
https://gitlab.com/gitlab-org/gitlab-workhorse/issues/61


Gitlab API
----------
- REST API Reference https://github.com/gitlabhq/gitlabhq/tree/master/doc/api
- Python API http://python-gitlab.readthedocs.io/en/stable/api-usage.html


Prometheus Exporter
-------------------
https://github.com/prometheus/client_python

Clearing Gitlab's Sidekiq Counters
----------------------------------
For an omnibus install::

   /opt/gitlab/embedded/bin/redis-cli -s '/var/opt/gitlab/redis/redis.socket' del resque:gitlab:stat:processed
   /opt/gitlab/embedded/bin/redis-cli -s '/var/opt/gitlab/redis/redis.socket' del resque:gitlab:stat:failed

http://stackoverflow.com/questions/15834911/how-do-i-reset-my-sidekiq-counters
