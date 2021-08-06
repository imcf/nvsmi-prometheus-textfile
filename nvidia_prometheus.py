#!/usr/bin/env python

"""Simple metrics collection via `nvidia-smi` in Prometheus textfile format."""

# pylint: disable-msg=invalid-name

from __future__ import print_function

import subprocess
import csv


class NvMetric(object):

    """Simple object for storing and accessing NVIDIA metrics, descriptions, etc."""

    def __init__(self, metric_name, description, value_type):
        self.name = metric_name
        self.name_suffix = ""
        self.description = description
        self.convert = None
        self.value_type = value_type
        if value_type == "pct":
            self.value_type = "int"
            self.convert = self.convert_percent
            self.name_suffix = "_ratio"
        elif value_type == "mb":
            self.value_type = "int"
            self.convert = self.convert_mb
            self.name_suffix = "_bytes"
        self.enabled = True
        self._value = None

    @property
    def value(self):
        """Get the value associated with this metric."""
        return self._value

    @value.setter
    def value(self, new_value):
        """Set the value associated with this metric, stripping surrounding whitespace.

        Parameters
        ----------
        new_value
            The value to be stored in this metric.
        """
        # print("%s -> <%s>" % (self, new_value))
        self._value = new_value.strip()
        if self.value_type == "str":
            return
        self._value = self._value.split(" ")[0]

    @property
    def prometheus_name(self):
        """Return the name in a Prometheus compatible format.

        Returns
        -------
        str
            The metric name where all dots are replaced by underscores.
        """
        return self.name.replace(".", "_")

    @staticmethod
    def convert_mb(value):
        """Transform a value given in megabytes into bytes (SI).

        Parameters
        ----------
        value : int
            The value in megabytes.

        Returns
        -------
        int
            The value multiplied by 1024
        """
        return int(value) * 1024

    @staticmethod
    def convert_percent(value):
        """Transform a percentage value from 0-100 into a decimal ratio (0-1).

        Parameters
        ----------
        value : int
            The percentage value as an integer.

        Returns
        -------
        float
            The value converted to the 0-1 range.
        """
        ratio = float(value) / 100.0
        return ratio

    def format_prometheus(self, labels):
        """Format the metric in Prometheus style, adding labels as provided.

        Parameters
        ----------
        labels : str
            A string that should be added as labels.

        Returns
        -------
        str
            The metric formatted for Prometheus.
        """
        if not self.enabled:
            return None
        value = self.value
        if self.convert:
            value = self.convert(value)
        name = self.prometheus_name + self.name_suffix
        if self.value_type == "str":
            labels += ', %s="%s"' % (self.name, value)
            value = 1
            name += "_info"
        return "nvsmi_%s{%s} %s" % (name, labels, value)

    def disable(self):
        """Set this metric's status to 'disabled'."""
        self.enabled = False

    def __str__(self):
        return '%s="%s"' % (self.prometheus_name, self.value)


# the list of properties to query for using "nvidia-smi":
metrics = [
    NvMetric("driver_version", "NVIDIA display driver version", "str"),
    NvMetric("gpu_serial", "the serial number physically printed on the board", "str"),
    # NvMetric("gpu_uuid", "globally unique immutable alphanumeric identifier", "str"),
    NvMetric("gpu_name", "official product name of the GPU", "str"),
    NvMetric("utilization.gpu", "percent of time the GPU was busy", "pct"),
    NvMetric("utilization.memory", "percent of time GPU RAM was read / written", "pct"),
    NvMetric("memory.total", "total installed GPU RAM", "mb"),
    NvMetric("memory.free", "total free GPU RAM", "mb"),
    NvMetric("memory.used", "total GPU RAM used by active contexts", "mb"),
    NvMetric("temperature.gpu", "core GPU temperature in degrees C", "int"),
    NvMetric("fan.speed", "intended (NOT MEASURED!) fan speed in percent", "int"),
    NvMetric("power.draw", "power draw for the entire board in Watts", "float"),
    NvMetric("power.limit", "software power limit in Watts", "float"),
    NvMetric("pci.domain", "PCI domain number", "hex"),
    NvMetric("pci.bus", "PCI bus number", "hex"),
    NvMetric("pci.device", "PCI device number", "hex"),
    NvMetric("pci.device_id", "PCI vendor device id", "hex"),
    NvMetric("pcie.link.gen.current", "current PCI-E link generation", "int"),
    NvMetric(
        "pcie.link.gen.max",
        "maximum PCI-E link generation possible with this GPU and system",
        "int",
    ),
    NvMetric("pcie.link.width.current", "current PCI-E link width", "int"),
    NvMetric(
        "pcie.link.width.max",
        "maximum PCI-E link width possible with this GPU and system configuration",
        "int",
    ),
]

# a list of PROPERTIES that should be used as labels for all Prometheus metrics:
use_as_label = [
    "gpu_serial",
    "gpu_name",
    "pci.domain",
    "pci.bus",
    "pci.device",
    "pci.device_id",
]

# create a dict with our metric objects so they are quickly accessible by their name:
metrics_by_name = dict()
for metric in metrics:
    metrics_by_name[metric.name] = metric

# create a list with the existing metric names:
metrics_names = [x.name for x in metrics]

smi_cmd = [
    "nvidia-smi",
    "--query-gpu=%s" % ",".join(metrics_names),
    "--format=csv",
]
# print(smi_cmd)

proc = subprocess.Popen(smi_cmd, stdout=subprocess.PIPE)
stdout = proc.communicate()[0].split("\n")
# print(stdout)

header = stdout.pop(0)  # remove header but remember it (might be useful at some point)
# print(header)

reader = csv.reader(stdout, delimiter=",")
for csv_line in reader:
    # skip the line if its length is zero:
    if not csv_line:
        continue

    for i, val in enumerate(csv_line):
        metrics[i].value = val

    # for metric in metrics:
    #     print("%s: %s" % (metric.name, metric.value))


# create a list of Prometheus-style label names from the NVIDIA SMI property names:
label_list = ["%s" % metrics_by_name[name] for name in use_as_label]
label_string = ", ".join(label_list)
# print(label_string)

for metric in metrics:
    if metric.name in use_as_label:
        continue
    print(metric.format_prometheus(label_string))
