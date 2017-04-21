# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Load test for the SyncStorage server
"""
import random
import time
from urllib.parse import urlparse, urlunparse

from tokenlib import make_token, get_derived_secret as derive
import browserid.jwt
import browserid.tests.support

from molotov import json_request, global_setup, set_var, get_var, scenario


# Assertions are good for one year (in seconds).
# This avoids having to deal with clock-skew in tokenserver requests.
ASSERTION_LIFETIME = 60 * 60 * 24 * 365

MOCKMYID_DOMAIN = "mockmyid.s3-us-west-2.amazonaws.com"
MOCKMYID_PRIVATE_KEY = browserid.jwt.DS128Key({
    "algorithm": "DS",
    "x": "385cb3509f086e110c5e24bdd395a84b335a09ae",
    "y": "738ec929b559b604a232a9b55a5295afc368063bb9c20fac4e53a74970a4db795"
         "6d48e4c7ed523405f629b4cc83062f13029c4d615bbacb8b97f5e56f0c7ac9bc1"
         "d4e23809889fa061425c984061fca1826040c399715ce7ed385c4dd0d40225691"
         "2451e03452d3c961614eb458f188e3e8d2782916c43dbe2e571251ce38262",
    "p": "ff600483db6abfc5b45eab78594b3533d550d9f1bf2a992a7a8daa6dc34f8045a"
         "d4e6e0c429d334eeeaaefd7e23d4810be00e4cc1492cba325ba81ff2d5a5b305a"
         "8d17eb3bf4a06a349d392e00d329744a5179380344e82a18c47933438f891e22a"
         "eef812d69c8f75e326cb70ea000c3f776dfdbd604638c2ef717fc26d02e17",
    "q": "e21e04f911d1ed7991008ecaab3bf775984309c3",
    "g": "c52a4a0ff3b7e61fdf1867ce84138369a6154f4afa92966e3c827e25cfa6cf508b"
         "90e5de419e1337e07a2e9e2a3cd5dea704d175f8ebf6af397d69e110b96afb17c7"
         "a03259329e4829b0d03bbc7896b15b4ade53e130858cc34d96269aa89041f40913"
         "6c7242a38895c9d5bccad4f389af1d7a4bd1398bd072dffa896233397a",
})


_DEFAULT = "https://token.stage.mozaws.net"


class TokenCreator(object):
    def __init__(self, server_url=_DEFAULT):
        self.timeskew = 0
        self.server_url = server_url
        self.auth_token = None
        self.auth_secret = None
        self.endpoint_url = None
        self.generate()

    def __repr__(self):
        return str(self.auth_token)

    def generate(self):
        """Pick an identity, log in and generate the auth token."""
        # If the server_url has a hash fragment, it's a storage node and
        # that's the secret.  Otherwise it's a token server url.
        uid = random.randint(1, 1000000)
        url = urlparse(self.server_url)
        if url.fragment:
            endpoint = url._replace(fragment="", path="/1.5/" + str(uid))
            self.endpoint_url = urlunparse(endpoint)
            data = {
                "uid": uid,
                "node": urlunparse(url._replace(fragment="")),
                "expires": time.time() + ASSERTION_LIFETIME,
            }
            self.auth_token = make_token(data, secret=url.fragment)
            self.auth_secret = derive(self.auth_token, secret=url.fragment)
        else:
            email = "user%s@%s" % (uid, MOCKMYID_DOMAIN)
            exp = time.time() + ASSERTION_LIFETIME + self.timeskew
            assertion = browserid.tests.support.make_assertion(
                email=email,
                audience=self.server_url,
                issuer=MOCKMYID_DOMAIN,
                issuer_keypair=(None, MOCKMYID_PRIVATE_KEY),
                exp=int(exp * 1000),
            )
            token_url = self.server_url + "/1.0/sync/1.5"
            response = json_request(token_url, headers={
                "Authorization": "BrowserID " + assertion,
            })
            # Maybe timeskew between client and server?
            if response['status'] == 401:
                server_time = int(response['headers']["X-Timestamp"])
                self.timeskew = server_time - int(time.time())
                exp = time.time() + ASSERTION_LIFETIME + self.timeskew
                assertion = browserid.tests.support.make_assertion(
                    email=email,
                    audience=self.server_url,
                    issuer=MOCKMYID_DOMAIN,
                    issuer_keypair=(None, MOCKMYID_PRIVATE_KEY),
                    exp=int(exp * 1000),
                )
                response = json_request(token_url, headers={
                    "Authorization": "BrowserID " + assertion,
                })

            if response['status'] > 299:
                raise ValueError(response['status'])

            credentials = response['content']
            self.auth_token = credentials["id"].encode('ascii')
            self.auth_secret = credentials["key"].encode('ascii')
            self.endpoint_url = credentials["api_endpoint"]


@global_setup()
def set_token(args):
    set_var('token', TokenCreator())


@scenario(1)
async def test(session):
    print(get_var('token'))
