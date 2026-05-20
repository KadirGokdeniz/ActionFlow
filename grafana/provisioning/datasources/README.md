# grafana/provisioning/datasources/

## prometheus.yml
This file configures Grafana to use Prometheus as its default datasource.
Note: despite the name, this is a **Grafana datasource provisioning** file,
not a Prometheus scrape config.

The actual Prometheus scrape config lives in `prometheus/prometheus.yml`
(or is passed via Docker Compose environment).
