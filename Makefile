.PHONY: help build build-tag push
.DEFAULT_GOAL:= help
.ONESHELL:

DOCKER_IMAGE = gpii/couchdb-statefulset-assembler

help:                     ## Prints list of tasks
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' Makefile

build:                    ## Build image as latest
	docker build -t "${DOCKER_IMAGE}:latest" ./

build-tag:                ## Build image as tag (use CI_COMMIT_TAG env var)
	@CI_COMMIT_TAG="$${CI_COMMIT_TAG:?Required variable not set}"
	docker build -t "${DOCKER_IMAGE}:${CI_COMMIT_TAG}" ./

push:                     ## Push image - latest
	docker push "${DOCKER_IMAGE}:latest"

push-tag:                 ## Push image - tag
	@CI_COMMIT_TAG="$${CI_COMMIT_TAG:?Required variable not set}"
	docker push "${DOCKER_IMAGE}:${CI_COMMIT_TAG}"
