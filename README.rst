Storage load test
-----------------
* Note: this requires Python version 3.5

To run it locally::

    $ virtualenv . -p python3.5
    $ bin/pip install -r requirements.txt
    $ bin/molotov --max-runs 5 -cxv loadtest.py


To run it locally, directly from Github (assuming Molotov is installed)::

    $ moloslave https://github.com/mozilla-services/syncstorage-loadtest test

See the molotov.json file for the different tests available to moloslave

To run it inside docker::

    $ docker run -e TEST_REPO=https://github.com/mozilla-services/syncstorage-loadtest -e TEST_NAME=test tarekziade/molotov:latest


Happy Breaking!
