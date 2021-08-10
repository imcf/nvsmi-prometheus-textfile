#!/usr/bin/env python

"""Simple metrics collection via `nvidia-smi` in Prometheus textfile format."""

# pylint: disable-msg=invalid-name

from __future__ import print_function

import subprocess
import csv
import copy
import logging

LOG = logging.getLogger()
LOG.addHandler(logging.StreamHandler())
LOG.setLevel(logging.WARNING)
# LOG.setLevel(logging.DEBUG)


class NvMetric(object):

    """Simple object for storing and accessing NVIDIA metrics, descriptions, etc."""

    def __init__(self, metric_name, description, value_type):
        self.name = metric_name
        self.name_suffix = ""
        self.description = description
        self._convert = None
        self.value_type = value_type
        if value_type == "pct":
            self.value_type = "int"
            self.name_suffix = "_ratio"
            self._convert = self.convert_percent
        elif value_type == "mb":
            self.value_type = "int"
            self.name_suffix = "_bytes"
            self._convert = self.convert_mb
        elif value_type == "degc":
            self.value_type = "int"
            self.name_suffix = "_celsius"
        elif value_type == "watt":
            self.value_type = "float"
            self.name_suffix = "_watts"
        self.enabled = True
        self._value = None

    @property
    def value(self):
        """Get the value associated with this metric, or `None` if it's disabled."""
        if not self.enabled:
            return None
        return self._value

    @value.setter
    def value(self, new_value):
        """Set the value associated with this metric after processing it.

        The setter will first strip surrounding whitespace from the new value. Then it
        checks for specific contents and takes special action, e.g. in case the new
        value is "[Not Supported]" (literally) it will NOT set the value (leaving it to
        `None`) and set the metric's `enabled` attribute to `False`. Eventually, it will
        split the new value on spaces and only keep the first segment (to remove
        possible unit strings that are usually returned by `nvidia-smi`) unless the
        `value_type` attribute is set to `str` (in which case it will literally keep the
        entire string value).

        Parameters
        ----------
        new_value
            The value to be stored in this metric.
        """
        LOG.debug("%s -> <%s>", self, new_value)
        self._value = new_value.strip()
        if self.value == "[Not Supported]":
            self.disable()
            return
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
            The value multiplied by 1024 * 1024
        """
        return int(value) * 1024 * 1024

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
            return ""

        if self._convert:
            try:
                value = self._convert(self.value)
            except ValueError:
                # in case conversion fails with a `ValueError` we silently skip the
                # entire metric for the output:
                return ""
            except Exception as err:  # pylint: disable-msg=broad-except
                LOG.error("Error converting value '%s': %s", self.value, err)
                return ""

        name = "nvsmi_" + self.prometheus_name + self.name_suffix
        if self.value_type == "str":
            labels += ', %s="%s"' % (self.name, value)
            value = 1
            name += "_info"
        formatted = "# HELP %s %s\n" % (name, self.description)
        formatted += "# TYPE %s gauge\n" % name
        formatted += "%s{%s} %s" % (name, labels, value)
        LOG.debug("formatted metric:\n----\n%s\n----\n", formatted)
        return formatted

    def disable(self):
        """Set this metric's status to 'disabled'."""
        LOG.info("Disabling metric '%s'...", self.name)
        self.enabled = False

    def __str__(self):
        return '%s="%s"' % (self.prometheus_name, self.value)


def process_gpu_metrics(values_from_csv):
    """Process one line of (parsed) CSV output from an `nvidia-smi` query.

    Parameters
    ----------
    values_from_csv : list(str)
        A single line of the parsed CSV, obtained e.g. by a `csv.reader()` call.
    """
    LOG.info("*** processing GPU metrics ***")
    LOG.debug("values_from_csv: %s", values_from_csv)

    # first we create a deep-copy of the metrics objects to be absolutely sure we don't
    # have any leftovers from previous calls:
    metrics = copy.deepcopy(METRICS)

    # create a shorthand-dict with our metric objects so we can access them by name:
    metrics_by_name = dict()
    for metric in metrics:
        metrics_by_name[metric.name] = metric

    # update the metric values from the given parsed CSV
    for i, val in enumerate(values_from_csv):
        metrics[i].value = val

    # create a list of Prometheus-style label names from the NVIDIA SMI property names:
    label_list = ["%s" % metrics_by_name[name] for name in USE_AS_LABEL]
    label_string = ", ".join(label_list)
    LOG.debug("label_string: %s", label_string)

    LOG.info("processed %s metrics, assembling Prometheus output...", len(metrics))
    output = list()
    for metric in metrics:
        if metric.name in USE_AS_LABEL:
            continue

        promethified = metric.format_prometheus(label_string)
        output.append(promethified)

    LOG.debug("%s\n", "".join(output))
    print("".join(output))


# the list of properties to query for using "nvidia-smi":
METRICS = [
    NvMetric("driver_version", "NVIDIA display driver version", "str"),
    NvMetric("gpu_serial", "the serial number physically printed on the board", "str"),
    # NvMetric("gpu_uuid", "globally unique immutable alphanumeric identifier", "str"),
    NvMetric("gpu_name", "official product name of the GPU", "str"),
    NvMetric("index", "zero-based index of the GPU, can change at each boot", "int"),
    NvMetric("utilization.gpu", "percent of time the GPU was busy", "pct"),
    NvMetric("utilization.memory", "percent of time GPU RAM was read / written", "pct"),
    NvMetric("memory.total", "total installed GPU RAM", "mb"),
    NvMetric("memory.free", "total free GPU RAM", "mb"),
    NvMetric("memory.used", "total GPU RAM used by active contexts", "mb"),
    NvMetric("temperature.gpu", "core GPU temperature in degrees C", "degc"),
    NvMetric("fan.speed", "intended (NOT MEASURED!) fan speed in percent", "pct"),
    NvMetric("power.draw", "power draw for the entire board in Watts", "watt"),
    NvMetric("power.limit", "software power limit in Watts", "watt"),
    NvMetric("pci.domain", "PCI domain number", "hex"),
    NvMetric("pci.bus", "PCI bus number", "hex"),
    NvMetric("pci.device", "PCI device number", "hex"),
    NvMetric("pci.device_id", "PCI vendor device id", "hex"),
    NvMetric(
        "pcie.link.gen.current",
        "current PCI-E link generation in use with this GPU and system",
        "int",
    ),
    NvMetric(
        "pcie.link.gen.max",
        "maximum PCI-E link generation possible with this GPU and system",
        "int",
    ),
    NvMetric(
        "pcie.link.width.current",
        "current PCI-E link width in use with this GPU and system",
        "int",
    ),
    NvMetric(
        "pcie.link.width.max",
        "maximum PCI-E link width possible with this GPU and system configuration",
        "int",
    ),
]

# a list of PROPERTIES that should be used as labels for all Prometheus metrics:
USE_AS_LABEL = [
    "gpu_serial",
    "gpu_name",
    "index",
    "pci.domain",
    "pci.bus",
    "pci.device",
    "pci.device_id",
]


# create a list with the existing metric names:
metrics_names = [x.name for x in METRICS]

smi_cmd = [
    "nvidia-smi",
    "--query-gpu=%s" % ",".join(metrics_names),
    "--format=csv",
]
LOG.info("call to `nvidia-smi`: <%s>", " ".join(smi_cmd))

proc = subprocess.Popen(smi_cmd, stdout=subprocess.PIPE)
stdout = proc.communicate()[0].split("\n")
LOG.debug("result from `nvidia-smi`:\n----\n%s\n----\n", stdout)

header = stdout.pop(0)  # remove header but remember it (might be useful at some point)
LOG.debug("header line:\n----\n%s\n----\n", header)

reader = csv.reader(stdout, delimiter=",")
for csv_line in reader:
    # skip the line if its length is zero:
    if not csv_line:
        continue

    process_gpu_metrics(csv_line)
