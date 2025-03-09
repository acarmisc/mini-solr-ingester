import json
import time
import os
from datetime import datetime
from kafka import KafkaConsumer
import pysolr
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('kafka-to-solr')

class KafkaToSolrProcessor:
    def __init__(self, kafka_bootstrap_servers, kafka_topic, solr_url, 
                 consumer_group_id, batch_size=50, max_wait_time=10, wait_time_empty_queue=300):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.wait_time_empty_queue = wait_time_empty_queue
        
        self.consumer = KafkaConsumer(
            kafka_topic,
            bootstrap_servers=kafka_bootstrap_servers,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id=consumer_group_id,
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        self.solr = pysolr.Solr(solr_url, always_commit=False)
        
        self.message_buffer = []
        
    def process(self):
        logger.info(f"Starting Kafka-to-Solr processor: batch_size={self.batch_size}, "
                    f"max_wait_time={self.max_wait_time}s, "
                    f"wait_time_empty_queue={self.wait_time_empty_queue}s")
        
        while True:
            try:
                self._process_batch()
                
                logger.info(f"No messages found in queue. Waiting {self.wait_time_empty_queue} seconds before retrying.")
                time.sleep(self.wait_time_empty_queue)
                
            except KeyboardInterrupt:
                logger.info("Execution interrupted. Shutting down...")
                if self.message_buffer:
                    self._insert_to_solr()
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(10)
        
        self.consumer.close()
    
    def _process_batch(self):
        last_insert_time = time.time()
        messages_processed = 0
        empty_polls = 0
        max_empty_polls = 5
        
        while True:
            message_batch = self.consumer.poll(timeout_ms=1000)
            
            if not message_batch:
                empty_polls += 1
                current_time = time.time()
                elapsed_time = current_time - last_insert_time
                
                if elapsed_time >= self.max_wait_time and self.message_buffer:
                    self._insert_to_solr()
                    last_insert_time = time.time()
                
                if empty_polls >= max_empty_polls:
                    if self.message_buffer:
                        self._insert_to_solr()
                    return
                
                continue
            
            empty_polls = 0
            
            for _, messages in message_batch.items():
                for message in messages:
                    self.message_buffer.append(message.value)
                    messages_processed += 1
                    
                    if len(self.message_buffer) >= self.batch_size:
                        self._insert_to_solr()
                        last_insert_time = time.time()
            
            current_time = time.time()
            elapsed_time = current_time - last_insert_time
            
            if elapsed_time >= self.max_wait_time and self.message_buffer:
                self._insert_to_solr()
                last_insert_time = time.time()
            
    def _insert_to_solr(self):
        num_messages = len(self.message_buffer)
        logger.info(f"Inserting {num_messages} documents to Solr")
        
        try:
            self.solr.add(self.message_buffer, commit=False)
            logger.info(f"Successfully inserted {num_messages} documents to Solr (without commit)")
        except Exception as e:
            logger.error(f"Error during Solr insertion: {e}")
        
        self.message_buffer = []


def get_env_var(var_name, default_value=None):
    value = os.environ.get(var_name)
    if value is None:
        if default_value is not None:
            logger.warning(f"Environment variable {var_name} not found. Using default value: {default_value}")
            return default_value
        else:
            raise ValueError(f"Environment variable {var_name} not found and no default value specified.")
    return value


if __name__ == "__main__":
    KAFKA_BOOTSTRAP_SERVERS = get_env_var('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    KAFKA_TOPIC = get_env_var('KAFKA_TOPIC', 'my_topic')
    SOLR_URL = get_env_var('SOLR_URL', 'http://localhost:8983/solr/my_core')
    CONSUMER_GROUP_ID = get_env_var('CONSUMER_GROUP_ID', 'solr-indexer')
    BATCH_SIZE = int(get_env_var('BATCH_SIZE', '50'))
    MAX_WAIT_TIME = int(get_env_var('MAX_WAIT_TIME', '10'))
    WAIT_TIME_EMPTY_QUEUE = int(get_env_var('WAIT_TIME_EMPTY_QUEUE', '300'))
    
    logger.info(f"Configuration loaded from environment variables:")
    logger.info(f"KAFKA_BOOTSTRAP_SERVERS: {KAFKA_BOOTSTRAP_SERVERS}")
    logger.info(f"KAFKA_TOPIC: {KAFKA_TOPIC}")
    logger.info(f"SOLR_URL: {SOLR_URL}")
    logger.info(f"CONSUMER_GROUP_ID: {CONSUMER_GROUP_ID}")
    logger.info(f"BATCH_SIZE: {BATCH_SIZE}")
    logger.info(f"MAX_WAIT_TIME: {MAX_WAIT_TIME}")
    logger.info(f"WAIT_TIME_EMPTY_QUEUE: {WAIT_TIME_EMPTY_QUEUE}")
    
    processor = KafkaToSolrProcessor(
        kafka_bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        kafka_topic=KAFKA_TOPIC,
        solr_url=SOLR_URL,
        consumer_group_id=CONSUMER_GROUP_ID,
        batch_size=BATCH_SIZE,
        max_wait_time=MAX_WAIT_TIME,
        wait_time_empty_queue=WAIT_TIME_EMPTY_QUEUE
    )
    
    processor.process()
