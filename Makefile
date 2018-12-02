REPO = "tsocial/cabot"

.PHONY: all test clean

all: docker_build

docker_login:
	echo "$(DOCKER_PASSWORD)" | docker login -u "$(DOCKER_USERNAME)" --password-stdin

docker_build:
	docker-compose build

docker_upload: docker_login
	docker-compose push
	# docker tag $(REPO):latest $(REPO):$(TRAVIS_BRANCH)-$(TRAVIS_BUILD_NUMBER)
	# docker push $(REPO):$(TRAVIS_BRANCH)-$(TRAVIS_BUILD_NUMBER)
	docker tag $(REPO):latest $(REPO):master-latest
	docker push $(REPO):master-latest
