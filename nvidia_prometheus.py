#!/usr/bin/env python

"""Simple metrics collection via `nvidia-smi` generating a Prometheus textfile."""

import subprocess
import csv
# from StringIO import StringIO


class NvMetric(object):

    """Simple object for storing and accessing NVIDIA metrics, descriptions, etc."""

    def __init__(self, metric_name, description, value_type):
        self.name = metric_name
        self.description = description
        self.value_type = value_type
        self.enabled = True
        self._value = None

    @property
    def value(self):
        """Get the value associated with this metric."""
        return self._value

    @value.setter
    def value(self, new_value):
        """Set the value associated with this metric.

        Parameters
        ----------
        new_value
            The value to be stored in this metric.
        """
        self._value = new_value

    def prometheus_name(self):
        """Return the name in a Prometheus compatible format.

        Returns
        -------
        str
            The metric name where all dots are replaced by underscores.
        """
        return self.name.replace(".", "_")

    def disable(self):
        """Set this metric's status to 'disabled'."""
        self.enabled = False


# the list of properties to query for using "nvidia-smi":
properties = [
    "driver_version",
    "gpu_serial",  # matches the serial number physically printed on each board
    "gpu_uuid",
    "gpu_name",
    "utilization.gpu",
    "utilization.memory",
    "memory.total",
    "memory.free",
    "memory.used",
    "temperature.gpu",
    "fan.speed",
    "power.draw",
    "power.limit",
    "pci.domain",
    "pci.bus",
    "pci.device",
    "pci.device_id",
    "pcie.link.gen.current",
    "pcie.link.gen.max",
    "pcie.link.width.current",
    "pcie.link.width.max",
]

metrics = [
    NvMetric("driver_version", "NVIDIA display driver version", "str"),
    NvMetric("gpu_serial", "the serial number physically printed on the board", "str"),
    NvMetric("gpu_uuid", "globally unique immutable alphanumeric identifier", "str"),
    NvMetric("gpu_name", "official product name of the GPU", "str"),
    NvMetric("utilization.gpu", "percent of time the GPU was busy", "int"),
    NvMetric("utilization.memory", "percent of time GPU RAM was read / written", "int"),
    NvMetric("memory.total", "total installed GPU RAM", "int"),
    NvMetric("memory.free", "total free GPU RAM", "int"),
    NvMetric("memory.used", "total GPU RAM allocated by active contexts", "int"),
    NvMetric("temperature.gpu", "core GPU temperature in degrees C", "int"),
    NvMetric("fan.speed", "intended (NOT MEASURED!) fan speed in percent", "int"),
    NvMetric("power.draw", "power draw for the entire board in Watts", "float"),
    NvMetric("power.limit", "software power limit in Watts", "float"),
    NvMetric("pci.domain", "PCI domain number", "hex"),
    NvMetric("pci.bus", "PCI bus number", "hex"),
    NvMetric("pci.device", "PCI device number", "hex"),
    NvMetric("pci.device_id", "PCI vendo device id", "hex"),
    NvMetric("pcie.link.gen.current", "current PCI-E link generation", "int"),
    NvMetric(
        "pcie.link.gen.max",
        "maximum PCI-E link generation possible with this GPU and system",
        "int"
    ),
    NvMetric("pcie.link.width.current", "current PCI-E link width", "int"),
    NvMetric(
        "pcie.link.width.max",
        "maximum PCI-E link width possible with this GPU and system configuration",
        "int"
    ),
]

metrics_dict = dict()
for metric in metrics:
    metrics_dict[metric.name] = metric


# build a second list compatible with Prometheus names (replacing dots by underscores)
prometheus_names = [ x.replace(".", "_") for x in properties]

smi_cmd = [
    "nvidia-smi",
    "--query-gpu=%s" % ",".join(properties),
    "--format=csv",
]
# print smi_cmd

proc = subprocess.Popen(smi_cmd, stdout=subprocess.PIPE)
out = proc.communicate()[0].split("\n")
# print out

header = out.pop(0)  # remove the header but remember it (might be useful at some point)
# print header

reader = csv.reader(out, delimiter=',')
for csv_line in reader:
    # skip the line if its length is zero:
    if not csv_line:
        continue

    gpu_metrics = dict()
    # print "\t".join(csv_line)
    for i, value in enumerate(csv_line):
        key = prometheus_names[i]
        # strip surrounding white spaces from the value:
        value = value.strip()
        # some values (e.g. the name) contain spaces, they should be kept as-is:
        if key in ["gpu_name", "driver_version"]:
            gpu_metrics[key] = value
            continue
        # all other values have their unit as a suffix which has to be stripped:
        gpu_metrics[key] = value.split(" ")[0]

    driver = gpu_metrics.pop("driver_version")
    serial = gpu_metrics.pop("gpu_serial")
    uuid = gpu_metrics.pop("gpu_uuid")
    name = gpu_metrics.pop("gpu_name")
    domain = gpu_metrics.pop("pci_domain")
    bus = gpu_metrics.pop("pci_bus")
    device = gpu_metrics.pop("pci_device")
    device_id = gpu_metrics.pop("pci_device_id")
    for key in gpu_metrics:
        print (
            (
                'nvsmi_%s{'
                    'driver="%s", '
                    'serial="%s", '
                    # 'uuid="%s", '
                    'name="%s", '
                    'pci_domain="%s", '
                    'pci_bus="%s", '
                    'pci_device="%s"'
                '} %s'
            )
            % (
                key,
                driver,
                serial,
                # uuid,
                name,
                domain,
                bus,
                device,
                gpu_metrics[key]
            )
        )
