# CouchDB StatefulSet Assembler

This code is intended to be deployed as a sidecar container in a Pod alongside
the [semi-official CouchDB Docker
image](https://hub.docker.com/r/apache/couchdb/) when running CouchDB as a
Kubernetes StatefulSet. It will resolve the DNS records maintained by Kubernetes
to discover the other peers in the cluster, then automatically populate the
Pod's _nodes DB with the names of the other nodes. The end result is that the
cluster is automically joined up.

If the deployment is scaled *up* after the initial creation those new Pods will
be automatically added. Scaling *down* does not automatically remove the Pods
from the membership database at this time.

## Building

### Master

On push/merge to master, CI will automatically build and push
`gpii/couchdb-statefulset-assembler:latest` image.

### Tags

Create and push git tag and CI will build and publish corresponding `gpii/couchdb-statefulset-assembler:${git_tag}` docker image.

#### Tag format

Tags should follow actual couchdb-statefulset-assembler version, suffixed by
`-gpii.${gpii_build_number}`, where `gpii_build_number` is monotonically
increasing number denoting Docker image build number,  starting from `0`
for each upstream version.

Example:
```
0.0.3-gpii.0
0.0.3-gpii.1
...
0.0.4-gpii.0
```

### Manually

Run `make` to see all available steps.
