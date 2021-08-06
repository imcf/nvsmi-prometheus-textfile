# Prometheus textfile collector for `nvidia-smi`

This is a zero-dependencies (see below for details) standalone tool collecting metrics
using the [`nvidia-smi`][1] (NVIDIA System Management Interface) command and formatting
them in a [Prometheus][2] compatible style that can be used through the
[node_exporter][3]'s `textfile` collector.

## Zero Dependencies / Why not using the official Prometheus Python Client?

The tool is intended to work on minimalistic installations, e.g. we are using it on our
[Xen][4] / [Citrix Hypervisor][5] instances. Those setups come with very basic installs
(currently based on [CentOS][6]) and there is a certain intrinsic risk of messing things
up by installing additional stuff like e.g. `pip` (which would be required for the
Python Client).

Therefore the only *actual* dependencies of this collector are already always fulfilled
on the relevant systems:

* Python 2.7 - comes with the base OS installation
* `nvidia-smi` - available as soon as the NVIDIA driver package is installed

## Seriously, Python 2.7? In 2021??

Well, that's what is available on the Citrix Hypervisor default installation that we're
running. Let's re-evaluate the situation with the next version.

[1]: https://developer.nvidia.com/nvidia-system-management-interface
[2]: https://prometheus.io/
[3]: https://github.com/prometheus/node_exporter
[4]: https://xenproject.org/
[5]: https://docs.citrix.com/en-us/citrix-hypervisor.html
[6]: https://centos.org/
