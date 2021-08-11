# Prometheus textfile collector for `nvidia-smi`

This is a zero-dependencies (see below for details) standalone tool collecting metrics
using the [`nvidia-smi`][1] (NVIDIA System Management Interface) command and formatting
them in a [Prometheus][2] compatible style that can be used through the
[node_exporter][3]'s `textfile` collector.

## Zero Dependencies / Why not using the official Prometheus Python Client?

The tool is intended to work on minimalistic installations, e.g. we are using it on our
[Xen][4] / [Citrix Hypervisor][5] instances. Those setups come with very basic installs
(currently based on [CentOS][6]) and the installation of additional tools like `pip`
(which would be required for the Python Client) is not always possible / desirable.

Therefore the only *actual* dependencies of this collector are already always fulfilled
on the relevant systems:

* Python 2.7 - comes with the base OS installation
* `nvidia-smi` - available as soon as the NVIDIA driver package is installed

## Permissions

No *root permissions* are required to collect the metrics through `nvidia-smi`, instead
having a user that is having write permissions to the textfile collector directory (or
actually just a single file therein, to be precise) of `node_exporter` is sufficient.

One simple solution is to run the script under the same account that is also used for
the `node_exporter`. A possible setup could look like this:

```bash
adduser \
    --home-dir /var/lib/node_exporter \
    --comment "Prometheus Node Exporter daemon" \
    --system \
    node_exporter

mkdir -pv /var/lib/node_exporter/textfile_collector
chown -R node_exporter:node_exporter /var/lib/node_exporter
```

## Running

Assuming you have cloned this repo to `/opt/nvsmi-prometheus-textfile/` and followed the
strategy for the user account outlined above, you could run the script to collect
metrics e.g. once a minute like so:

```bash
su - node_exporter
OUTFILE="/var/lib/node_exporter/textfile_collector/nvsmi.prom"
while true ; do
    /opt/nvsmi-prometheus-textfile/nvidia_prometheus.py > $OUTFILE
    sleep 60
done
```

## Seriously, Python 2.7? In 2021??

Well, that's what is available on the Citrix Hypervisor default installation that we're
running. Let's re-evaluate the situation with the next version.

## Metric and Label Naming

See the official Prometheus instructions on [writing exporters][7] and [metric and
label naming][8] for more information.

[1]: https://developer.nvidia.com/nvidia-system-management-interface
[2]: https://prometheus.io/
[3]: https://github.com/prometheus/node_exporter
[4]: https://xenproject.org/
[5]: https://docs.citrix.com/en-us/citrix-hypervisor.html
[6]: https://centos.org/
[7]: https://prometheus.io/docs/instrumenting/writing_exporters/
[8]: https://prometheus.io/docs/practices/naming/
