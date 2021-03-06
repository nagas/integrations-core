# Activemq_xml Integration

## Overview

Get metrics from activemq_xml service in real time to:

* Visualize and monitor activemq_xml states
* Be notified about activemq_xml failovers and events.

## Setup
### Installation

Install the `dd-check-activemq_xml` package manually or with your favorite configuration manager

### Configuration

Edit the `activemq_xml.yaml` file to point to your server and port, set the masters to monitor

### Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        activemq_xml
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The activemq_xml check is compatible with all major platforms

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/activemq_xml/metadata.csv) for a list of metrics provided by this integration.

### Events
The Activemq_xml check does not include any event at this time.

### Service Checks
The Activemq_xml check does not include any service check at this time.

## Further Reading
### Blog Article
See our blog post [Monitor ActiveMQ metrics and performance](https://www.datadoghq.com/blog/monitor-activemq-metrics-performance/)
