# F-UJI configuration options

Since version 3.0.0 F-UJI offers a variety of configuration options which allows to use user defined metrics and to restrict metadata harvesting methods.

## Metric YAML

You can define your own metric definitions in a dedicated YAML file. Metrics YAML files have to comply with the following conventions:

* Files need to be located in folder 'yaml'
* File names have to follow this syntax: metrics_[version][community_code].yaml
	where [version] has to be a number  must be a number, which can optionally have one decimal point.

By now, user define metrics have to be based on metrics file 'metrics_0.6.yaml' which should be used as template.

Copy the YAML content of this metric file to a new metric file and save the file following the syntax mentioned above for the file name of the new metrics e.g. metrics_0.6new.yaml.

To define own metrics you can restrict the number of metrics and add configuration options to a limited number of existing metrics.

### Configure metrics and tests to be performed

To restrict metrics choose those you want to use from the 0.6 list of metrics and tests and simply delete tests or metrics which you do not wish to be performed during your assessments.

### Configure individual metrics tests

For all metrics and tests you can change the YAML properties*metric_short_name*, *metric_name* and *description* according to your needs.

For some tests you can define additional parameters. For example, one can specify exactly which metadata elements, licenses, metadata standards or vocabularies are expected.

Generally, these specifications are defined using the YAML property *community_requirements* which has to be a dictionary containing the subproperties *target*, *modality*, and  *required*.

* *target* defines the test targets, defined in the F-UJI ontology, such as licenses, metadata properties etc. which is represented by a controlled list of values which is used for tests by default.
* *required* has to be a list which defines the necessary property values
* *modality* defines if *all* or *any* of *required* values need to be present to pass the test.
*match* specifies how matching values are identified: *wildcard* for wildcard-like match rules like 'test*'; *full* when a full match is required.
*target_property* additionally defines the property of the *target* object in which matches are searched for, by default the property *name* or *label* is used for this purpose.
*modality* and *match* are currently not yet implemented, thus still hardcoded :( but may be implemented in future versions.

## Selectin a metric within an API call

Within the POST data you need to specify the metric which has to be used. To do this, use the *metric_version* argument:
~~~
{
  "object_identifier": "https://doi.org/10.1594/PANGAEA.908011",
  "test_debug": true,
  "metadata_service_endpoint": "http://ws.pangaea.de/oai/provider",
  "metadata_service_type": "oai_pmh",
  "use_datacite": true,
  "use_github": false,
  "metric_version": "metrics_v0.5"
}
~~~
