#!/usr/bin/env python
# encoding: utf-8

import logging
import os
from datetime import datetime
import time

import gitlab
from prometheus_client import start_http_server, Summary, Gauge

try:
    loglevel = getattr(logging, os.environ.get('LOGLEVEL', 'WARN').upper())
except AttributeError:
    pass

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(level=loglevel)

# time to sleep between calls to gitlab
INTERVAL = int(os.environ.get('INTERVAL', 300))

# port to listen on
PORT = int(os.environ.get('PORT', 3001))

# URL of the GitLab instance, defaults to hosted GitLab
URL = str(os.environ.get('URL', 'https://gitlab.com'))

# Secret token for the app to authenticate itself
TOKEN = str(os.environ.get('TOKEN'))

# Secret token for the app to authenticate itself
VERSION = int(os.environ.get('VERSION', 4))

# Login to GitLab
gl = gitlab.Gitlab(URL, TOKEN, api_version=VERSION)
gl.auth()

# Initialize Prometheus instrumentation
projects_total = Gauge(
    'gitlab_projects_total',
    'Number of projects'
)
jobs_total = Gauge(
    'gitlab_jobs_total',
    'Number of jobs',
    ['namespace', 'project_id', 'project_name']
)
job_duration_seconds = Summary(
    'gitlab_job_duration_seconds',
    'Seconds the job took to run',
    ['namespace', 'project_id', 'project_name', 'stage', 'status', 'ref']
)
pipeline_duration_seconds = Summary(
    'gitlab_pipeline_duration_seconds',
    'Seconds the pipeline took to run',
    ['namespace', 'project_id', 'project_name', 'status', 'ref']
)


def get_projects():
    try:
        projects = gl.projects.list(all=True)
        log.debug("Projects: {}".format(projects))
        return projects
    except gitlab.exceptions.GitlabListError:
        log.warn("Projects could not be retrieved")
        return []

def get_jobs(project):
    try:
        jobs = project.jobs.list(all=True)
        log.debug("jobs: {}".format(jobs))
        return jobs
    except gitlab.exceptions.GitlabListError:
        log.warn("jobs could not be retrieved")
        return []


def get_duration(process):
    try:
        start = datetime.strptime(process.started_at, "%Y-%m-%dT%H:%M:%S.%fZ")
        end = datetime.strptime(process.finished_at, "%Y-%m-%dT%H:%M:%S.%fZ")
        duration = end - start
        return duration
    except TypeError:
        return 0


def get_pipelines(project):
    try:
        pipelines = project.pipelines.list(all=True)
        log.debug("Pipelines: {}".format(pipelines))
        return pipelines
    except gitlab.exceptions.GitlabListError:
        log.warn("Pipelines could not be retrieved")
        return []


def get_stats():
    projects = get_projects()
    projects_total.set(len(projects))

    for project in projects:
        namespace = project.namespace["name"]

        project = gl.projects.get(project.id)
        log.debug(
            "Namespace: {} Project: {} {}".format(
                namespace,
                project.name,
                project.id
            )
        )

        pipelines = get_pipelines(project)
        jobs = get_jobs(project)

        jobs_total.labels(
            namespace=namespace,
            project_id=project.id,
            project_name=project.name
        ).set(len(jobs))

        for pipeline in pipelines:
            try:
                duration = get_duration(pipeline)
                summary = pipeline_duration_seconds.labels(
                    namespace=namespace,
                    project_id=project.id,
                    project_name=project.name,
                    status=pipeline.status,
                    ref=pipeline.ref
                )
                summary.observe(duration.total_seconds())
            except AttributeError:
                pass
        for job in jobs:
            try:
                duration = get_duration(job)
                summary = job_duration_seconds.labels(
                    namespace=namespace,
                    project_id=project.id,
                    project_name=project.name,
                    stage=job.stage,
                    status=job.status,
                    ref=pipeline.ref
                )
                summary.observe(duration.total_seconds())
            except AttributeError:
                pass


if __name__ == '__main__':
    start_http_server(PORT)
    log.info('listening on port {0}'.format(PORT))
    while True:
        try:
            get_stats()
            log.info('sleeping for {0} seconds'.format(INTERVAL))
            time.sleep(INTERVAL)
        except KeyboardInterrupt:
            break
