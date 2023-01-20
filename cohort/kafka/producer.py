from json import dumps

from kafka import KafkaProducer

from cohort.kafka import SERVERS, COHORT_CREATION_REQUEST_TOPIC, _logger


def push_cohort_creation_to_queue(cohort_result_uuid: str, json_query: str):
    _logger.info(f"Pushing new message to the queue to create cohort with uuid:{cohort_result_uuid}")
    producer = KafkaProducer(bootstrap_servers=SERVERS,
                             value_serializer=lambda x: dumps(x).encode('utf-8'))
    producer.send(topic=COHORT_CREATION_REQUEST_TOPIC,
                  value={str(cohort_result_uuid): json_query})
    _logger.info(f"Done pushing to the queue, cohort_uuid: {cohort_result_uuid}")
