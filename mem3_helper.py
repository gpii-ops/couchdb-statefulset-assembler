"""Helper module to connect a CouchDB Kube StatefulSet

This script grabs the list of pod names behind the headless service
associated with our StatefulSet and feeds those as `couchdb@FQDN`
nodes to mem3.
"""

import json
import requests
import time
import dns.resolver
import socket
import backoff
import os
import sys

class PeerDiscoveryException(Exception):
    pass

def construct_service_record():
    # Drop our Pod's unique identity and replace with '_couchdb._tcp'
    return os.getenv('SRV_RECORD') or '.'.join(['_couchdb', '_tcp'] + socket.getfqdn().split('.')[1:])

@backoff.on_exception(
    backoff.expo,
    dns.resolver.NXDOMAIN,
    max_tries=15
)
@backoff.on_exception(
    backoff.expo,
    PeerDiscoveryException,
    max_tries=15
)
def discover_peers(service_record):
    expected_peers_count = os.getenv('COUCHDB_CLUSTER_SIZE')
    if expected_peers_count:
        expected_peers_count = int(expected_peers_count)
        print('Expecting', expected_peers_count, 'peers...')
    else:
        print('Looks like COUCHDB_CLUSTER_SIZE is not set, will not wait for DNS to fully propagate...')
    print('Resolving SRV record:', service_record)
    # Erlang requires that we drop the trailing period from the absolute DNS
    # name to form the hostname used for the Erlang node. This feels hacky
    # but not sure of a more official answer
    answers = dns.resolver.query(service_record, 'SRV')
    peers = [rdata.target.to_text()[:-1] for rdata in answers]
    peers_count = len(peers)
    if expected_peers_count:
        print('Discovered', peers_count, 'of', expected_peers_count, 'peers:', peers)
        if peers_count != expected_peers_count:
            print('Waiting for cluster DNS to fully propagate...')
            raise PeerDiscoveryException
    else:
        print('Discovered', peers_count, 'peers:', peers)
    return peers

@backoff.on_exception(
    backoff.expo,
    requests.exceptions.ConnectionError,
    max_tries=10
)
def connect_the_dots(names):
    creds = (os.getenv("COUCHDB_USER"), os.getenv("COUCHDB_PASSWORD"))
    for name in names:
        uri = "http://127.0.0.1:5986/_nodes/couchdb@{0}".format(name)
        doc = {}
        if creds[0] and creds[1]:
            resp = requests.put(uri, data=json.dumps(doc), auth=creds)
        else:
            resp = requests.put(uri, data=json.dumps(doc))
        while resp.status_code == 404:
            print('Waiting for _nodes DB to be created...')
            time.sleep(5)
            resp = requests.put(uri, data=json.dumps(doc))
        print('Adding cluster member', name, resp.status_code)
    print('Cluster membership populated!')

def check_membership_forever():
    creds = (os.getenv("COUCHDB_USER"), os.getenv("COUCHDB_PASSWORD"))
    expected_peers_count = os.getenv("COUCHDB_CLUSTER_SIZE")
    uri = "http://127.0.0.1:5984/_membership"
    print('Checking _membership data...')
    while True:
        if creds[0] and creds[1]:
            resp = requests.get(uri, auth=creds)
        else:
            resp = requests.get(uri)
        if resp.status_code != 200:
            print('ERROR: _membership responded with', resp.status_code, '!', file=sys.stderr)
        else:
            try:
                membership_json = json.loads(resp.text)
                if 'error' in membership_json:
                    print('ERROR: _membership response contains error:', membership_json['error'], '!', file=sys.stderr)
                elif 'cluster_nodes' in membership_json and 'all_nodes' in membership_json:
                    if membership_json['cluster_nodes'] != membership_json['all_nodes']:
                        print('ERROR: cluster_nodes contains:', membership_json['cluster_nodes'], 'while all_nodes contains:', membership_json['all_nodes'], '!', file=sys.stderr)
                    if expected_peers_count and len(membership_json['cluster_nodes']) < int(expected_peers_count):
                        print('ERROR: cluster_nodes contains', len(membership_json['cluster_nodes']), 'nodes, but expecting', expected_peers_count, 'nodes!', file=sys.stderr)
                else:
                    print('ERROR: _membership response does not contain expected data structure!', file=sys.stderr)
            except json.decoder.JSONDecodeError:
                print('ERROR: unable to decode JSON in _membership response!', file=sys.stderr)
        time.sleep(10)

if __name__ == '__main__':
    connect_the_dots(discover_peers(construct_service_record()))
    check_membership_forever()
