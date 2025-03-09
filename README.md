# Kafka to Solr Ingester

A lightweight Python application that consumes documents from a Kafka topic and indexes them into a Solr instance.

## Overview

This application serves as a simple yet efficient data pipeline between Kafka and Solr. It continuously consumes JSON documents from a specified Kafka topic and indexes them in batches to a Solr core without committing. The ingester follows these key behaviors:

- Collects messages in a buffer and indexes them to Solr after receiving 50 messages
- If fewer than 50 messages are received within 10 seconds, it indexes whatever is in the buffer
- After emptying the Kafka queue, it waits for 5 minutes before resuming consumption
- All configuration parameters can be customized via environment variables

## Configuration

The application is fully configurable through environment variables:

| Environment Variable | Description | Default Value |
|----------------------|-------------|---------------|
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker address(es) | `localhost:9092` |
| `KAFKA_TOPIC` | Kafka topic to consume from | `my_topic` |
| `SOLR_URL` | Solr URL including core name | `http://localhost:8983/solr/my_core` |
| `CONSUMER_GROUP_ID` | Kafka consumer group ID | `solr-indexer` |
| `PAYLOAD_FIELD` | Specific field from Kafka message to index (if not set, uses entire message) | Not set |
| `DESERIALIZE_TEXT` | Whether to deserialize string payloads as JSON | `False` |
| `BATCH_SIZE` | Number of messages to collect before indexing | `50` |
| `MAX_WAIT_TIME` | Maximum wait time in seconds before indexing | `10` |
| `WAIT_TIME_EMPTY_QUEUE` | Wait time in seconds after emptying the queue | `300` |

## Deployment

### Docker

The application can be containerized using Docker:

```bash
docker build -t kafka-to-solr:latest .
docker run -e KAFKA_BOOTSTRAP_SERVERS=my-kafka:9092 -e SOLR_URL=http://my-solr:8983/solr/my_core kafka-to-solr:latest
```

### Kubernetes

A deployment manifest is provided for Kubernetes, which includes:
- A ConfigMap for environment variables
- A Deployment with resource limits and health checks

```bash
kubectl apply -f kubernetes-manifest.yaml
```

## Dependencies

- Python 3.12+
- kafka-python
- pysolr

## License

[MIT License](LICENSE)
