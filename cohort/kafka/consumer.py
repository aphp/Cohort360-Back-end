from json import loads

from kafka import KafkaConsumer, ConsumerRebalanceListener

from cohort.kafka import SERVERS, COHORT_CREATION_RESPONSE_TOPIC, _logger


class CustomConsumerRebalanceListener(ConsumerRebalanceListener):
    pass


def consume_cohort_creation():
    _logger.info(f"*************  will start consuming from queue")
    consumer = KafkaConsumer(COHORT_CREATION_RESPONSE_TOPIC,
                             bootstrap_servers=SERVERS,
                             auto_offset_reset="earliest",
                             group_id="default_group",
                             value_deserializer=lambda x: loads(x.decode("utf-8")))
    for msg in consumer:
        pass

    consumer.subscribe(topics=COHORT_CREATION_RESPONSE_TOPIC,
                       listener=CustomConsumerRebalanceListener())

    consumer.close()
